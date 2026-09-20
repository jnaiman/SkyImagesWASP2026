"""
Parsing of raw LMM output, copied from the LLM_VQA_MultiPanel project
(utils/parse_lmm_output_utils.py, 2026-07-17) so this repo stops re-deriving it.

Only the response-side parsing is brought across.  `parse_json_files` and the
comparison helpers around it are left behind: they are tied to that project's
directory layout and its own dataframe schema, neither of which applies here.

Why this rather than a hand-rolled json.loads
---------------------------------------------
Models do not reliably return the JSON that was asked for.  Observed in the
n150 run alone: Claude answers the key `plot_types` (134/150) or `plot_type`
(11/150) when the prompt asked for `plot types`; answers arrive with trailing
commas, single quotes, unescaped LaTeX backslashes, mismatched braces, and the
answer and explanation sometimes merged into one object rather than two.
`parse_llm_dual_json` works through those cases in order and separates the
answer from the explanation by key name.

On `expected_keys`: leaving it None accepts whatever key came back, which is
what the upstream project does.  Passing the documented key makes any rename a
PARSE_ERROR -- honest, but it would score Claude 0 on the plot-type question
purely for using an underscore.  `answer_for` below takes the middle road: it
matches the requested key up to spacing/underscore/case, and only then falls
back to "the one non-explanation value".
"""

import pandas as pd
import json
import pickle
import numpy as np
from copy import deepcopy
import re
import ast
import warnings

PLACEHOLDER = "PARSE_ERROR"

def parse_llm_dual_json(
    output: str,
    expected_keys: list[str] | None = None
) -> tuple[str | None, dict | None]:
    """
    Parse LLM output containing an answer JSON and optional explanation JSON.

    Args:
        output: Raw LLM output string
        expected_keys: Optional list of keys the answer dict should contain.
                       If provided and answer doesn't match, returns PLACEHOLDER.

    Returns:
        (answer_str, explanation_dict)
        answer_str is PLACEHOLDER if parsing fails or schema doesn't match.
    """
    output = output.strip()

    def extract_json_objects(text):
        objects = []
        depth = 0
        start = None
        in_string = False
        escape_next = False

        for i, ch in enumerate(text):
            if escape_next:
                escape_next = False
                continue
            if ch == '\\' and in_string:
                escape_next = True
                continue
            if ch == '"' and not escape_next:
                in_string = not in_string
            if in_string:
                continue
            if ch == '{':
                if depth == 0:
                    start = i
                depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0 and start is not None:
                    objects.append(text[start:i+1])
                    start = None
        return objects

    def fix_mismatched_braces(obj_str: str) -> str:
        """Replace mismatched closing braces/brackets."""
        # Count opens vs closes for each type
        open_curly = obj_str.count('{')
        close_curly = obj_str.count('}')
        open_square = obj_str.count('[')
        close_square = obj_str.count(']')

        # Build a corrected string by walking and tracking a stack
        stack = []
        result = []
        in_string = False
        escape_next = False

        for ch in obj_str:
            if escape_next:
                escape_next = False
                result.append(ch)
                continue
            if ch == '\\' and in_string:
                escape_next = True
                result.append(ch)
                continue
            if ch == '"' and not escape_next:
                in_string = not in_string
                result.append(ch)
                continue
            if in_string:
                result.append(ch)
                continue

            if ch == '{':
                stack.append('}')
                result.append(ch)
            elif ch == '[':
                stack.append(']')
                result.append(ch)
            elif ch in ('}', ']'):
                if stack and stack[-1] == ch:
                    stack.pop()
                    result.append(ch)
                elif stack and stack[-1] != ch:
                    # Wrong closer — use the expected one instead
                    result.append(stack.pop())
                # else: extra closer with empty stack, drop it
            else:
                result.append(ch)

        # Close anything left open
        while stack:
            result.append(stack.pop())

        return ''.join(result)

    def try_parse(obj_str: str) -> dict | None:
        # 1. Strict parse
        try:
            return json.loads(obj_str)
        except json.JSONDecodeError:
            pass

        # 2. Fix mismatched braces/brackets then retry
        try:
            fixed = fix_mismatched_braces(obj_str)
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # 3. Strip trailing commas
        try:
            fixed = re.sub(r',\s*([}\]])', r'\1', obj_str)
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # 4. Single quotes only (when no double quotes present)
        if '"' not in obj_str:
            try:
                fixed = re.sub(r"'", '"', obj_str)
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass

        # 5. Stray mid-token quotes
        try:
            fixed = re.sub(r'(?<=[^\s,:\[{])\"(?=[^\s,:\]}\:])', '', obj_str)
            return json.loads(fixed)
        except json.JSONDecodeError:
            pass

        # 6. ast.literal_eval fallback
        #
        # literal_eval runs ast.parse underneath, so Python evaluates the text
        # as source and warns about any string escape it does not recognise --
        # '\d', '\s' and friends.  Model answers are full of those: a
        # declination axis labelled '$\delta$ (2000)' is a correct answer, and
        # 228 responses in the n150 run carry such a sequence.  The warning
        # names '<unknown>:1' because the text has no file, which makes it look
        # like a bug in this repo when it is neither our source nor an error.
        # Parsing untrusted text is the entire job of this branch, so the
        # warning is suppressed here and only here.
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', SyntaxWarning)
                result = ast.literal_eval(obj_str)
            if isinstance(result, dict):
                return result
        except (ValueError, SyntaxError):
            pass

        return None

    def split_combined(obj: dict, explanation_keys: set) -> tuple[dict | None, dict | None]:
        expl = {k: v for k, v in obj.items() if k in explanation_keys}
        ans = {k: v for k, v in obj.items() if k not in explanation_keys}
        return (ans if ans else None), (expl if expl else None)

    def validate_answer(ans: dict | None, expected_keys: list[str] | None) -> bool:
        """Check answer has expected keys and non-empty values."""
        if ans is None:
            return False
        if expected_keys is None:
            return True  # No schema to check against
        return all(k in ans and ans[k] not in (None, "", [], {}) for k in expected_keys)

    explanation_keys = {"explanation", "reason", "reasoning", "rationale"}
    raw_objects = extract_json_objects(output)

    parsed = []
    for obj_str in raw_objects:
        candidate = try_parse(obj_str)
        if candidate is not None:
            parsed.append(candidate)

    answer, explanation = None, None

    if len(parsed) == 0:
        pass

    elif len(parsed) == 1:
        obj = parsed[0]
        has_explanation = any(k in obj for k in explanation_keys)
        has_answer = any(k not in explanation_keys for k in obj)

        if has_explanation and has_answer:
            answer, explanation = split_combined(obj, explanation_keys)
        elif has_explanation:
            explanation = obj
        else:
            answer = obj

    else:
        for obj in parsed:
            if any(k in obj for k in explanation_keys):
                explanation = obj
            else:
                answer = obj

    # Validate answer against expected schema
    if not validate_answer(answer, expected_keys):
        answer_str = PLACEHOLDER
    else:
        answer_str = json.dumps(answer)

    return answer_str, explanation






########### HERE #############

def parse_first_json(text):
    decoder = json.JSONDecoder()
    obj, idx = decoder.raw_decode(text)
    return obj

# claude suggestions for fixing slashes
# Replace single backslashes with double backslashes in JSON strings
def fix_json_escapes(json_str):
    # This pattern finds backslashes that aren't already properly escaped
    return re.sub(r'(?<!\\)\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r'\\\\', json_str)

def fix_raw_strings(json_str):
    # Remove r" prefixes and escape backslashes in the content
    def replace_raw_string(match):
        content = match.group(1)
        # Escape backslashes
        escaped_content = content.replace('\\', '\\\\')
        return f'"{escaped_content}"'
    
    # Find r"..." patterns and replace them
    return re.sub(r'r"([^"]*)"', replace_raw_string, json_str)

# Or more comprehensive - escape all single backslashes before letters
def fix_all_latex(json_str):
    return re.sub(r'(?<!\\)\\(?=[a-zA-Z])', r'\\\\', json_str)

def fix_latex_math(json_str):
    # Add quotes around $...$ expressions
    return re.sub(r'\$([^$]+)\$', r'"\$\1\$"', json_str)


def fix_aspect(jllm):
    ar = jllm['aspect ratio']
    ar = ar.replace('approximately','')
    ar = ar.replace('~','')
    ar = ar.replace("≈",'')
    if "(" in ar:
        #jllm['aspect ratio'] = jllm['aspect ratio'].split('(')[0]
        #ar = jllm['aspect ratio'].split('(')[0]
        ar = ar.split('(')[0]
    if ' or ' in ar: # take last
        ar = ar.split(' or ')[-1]
    if ' to ' in ar: # take last
        ar = ar.split(' to ')[-1]
    if ':' in ar:
        #ans = ar #jllm['aspect ratio']
        #print(ans)
        try:
            ar = float(ar.split(':')[0])/float(ar.split(':')[1])
        except:
            ar = np.nan
    #print(ar)
    if not isinstance(ar,float):
        if '/' in ar:
            ar = float(ar.split('/')[0])/float(ar.split('/')[1]) 
    try:
        ar = float(ar)
    except:
        if '-' in ar:
            try: 
                f1 = float(ar.split('-'))[0]
            except:
                f1 = None
            try:
                f2 = float(ar.split('-'))[-1]
            except:
                f2 = None
            if f1 is not None and f2 is not None:
                ar = f2 # take last after split
            else:
                print('ar could not convert:', ar, ', orig:', jllm['aspect ratio'])
                lskjsl
    return ar


# ---------------------------------------------------------------- adapter ---
# Small layer over parse_llm_dual_json for this repo's notebooks.

_EXPLANATION_KEYS = {'explanation', 'reason', 'reasoning', 'rationale'}


def _norm_key(k):
    """Key identity ignoring spacing, underscores, hyphens and case."""
    return re.sub(r'[\s_\-]+', '', str(k)).lower()


def answer_for(raw, expected_key=None):
    """
    The model's answer, from a raw response string.

    expected_key : the key the prompt asked for, e.g. 'plot types'.  Matched up
        to spacing/underscore/case, so Claude's 'plot_types' still resolves.
        When it is absent entirely, the single non-explanation value is used --
        the answer is there, just labelled differently.

    Returns None when nothing usable came back, so callers can count
    unparseable answers separately from wrong ones.
    """
    answer_str, _ = parse_llm_dual_json(raw or '')
    if not answer_str or answer_str == PLACEHOLDER:
        return None
    try:
        ans = json.loads(answer_str)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(ans, dict) or not ans:
        return None

    if expected_key is not None:
        want = _norm_key(expected_key)
        for k, v in ans.items():
            if _norm_key(k) == want:
                return _unwrap(v)

    vals = [v for k, v in ans.items() if _norm_key(k) not in
            {_norm_key(e) for e in _EXPLANATION_KEYS}]
    return _unwrap(vals[0]) if len(vals) >= 1 else None


def _unwrap(v):
    """A one-element list is the asked-for shape for some questions."""
    if isinstance(v, list):
        return v[0] if v else None
    return v


def expected_key_from_format(fmt):
    """
    The key a prompt asked for, read out of its own format instruction.

    e.g. 'Please format the output as a json as {"plot types":[]}, where ...'
    -> 'plot types'.  Taken from the prompt rather than hard-coded so the two
    cannot drift apart.
    """
    if not fmt or '{' not in fmt:
        return None
    inner = fmt.split('{', 1)[1].split('}', 1)[0]
    if ':' not in inner:
        return None
    return inner.split(':', 1)[0].strip().strip('"').strip("'").strip()


def ground_truth(entry):
    """
    Ground truth for a qa entry, however it is stored.

    The plot-type question keeps it in a dict; the distribution question uses a
    bare string.  parse_qa in llm_utils makes the same distinction -- this is
    the response-side counterpart so callers need not care which they have.
    """
    a = entry.get('A')
    if isinstance(a, dict):
        a = list(a.values())[0] if a else None
    return _unwrap(a)

def normalise_numeric(text):
    """
    Math notation a model might emit, rewritten so float() accepts it.

    Lifted from `parse_json_files` upstream, where it is applied to the raw
    answer before json parsing.  Without it `1.2^-5`, `3.4**2`, `1.2e(-5)` and
    a unicode minus all become NaN and are scored as unparseable rather than
    as answers.

    Deliberately NOT applied inside answer_for: it rewrites '^' as an exponent
    marker, which is right for '1.2^-5' and wrong for a caret meaning anything
    else.  Callers working with numeric answers opt in.
    """
    if not isinstance(text, str):
        return text
    t = text.replace('^', 'e').replace('**', 'e')
    # 1.2e(-5) -> 1.2e-5
    t = re.sub(r'(\d*\.?\d+e)\s*\(\s*-\s*(\d+)\s*\)', r'\1-\2', t)
    t = t.replace('True', 'true').replace('False', 'false')
    t = t.replace('\u2212', '-')          # unicode minus
    return t


def as_float(x, numeric_fixes=True):
    """
    A single float out of a bare value, a nested dict, or a one-item list.

    numeric_fixes : run normalise_numeric on strings first.  NaN when nothing
        numeric can be recovered, so callers can count unparseable separately.
    """
    while isinstance(x, dict) and x:
        x = list(x.values())[0]
    if isinstance(x, (list, tuple)):
        x = x[0] if x else None
    if isinstance(x, str):
        x = x.replace(',', '').strip()
        if numeric_fixes:
            x = normalise_numeric(x)
    try:
        return float(x)
    except (TypeError, ValueError):
        return float('nan')
