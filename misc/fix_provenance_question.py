"""
Drop ", calculated from the data values used to create the plot" from the SKY
provenance question, and re-ask just that question.

Why
---
The provenance question asks whether a sky panel is a real survey cutout or a
gaussian mixture.  Its format string was inherited from the numeric questions
and ends "...should be a string, calculated from the data values used to
create the plot".  Nothing is being calculated here -- it is a judgement about
where the image came from -- and combined with the phrase "underlying
distribution" it invites reading the question as being about the statistical
distribution of pixel values instead.  All three models answer "real image of
the sky" 92-100% of the time regardless of the truth, so it is worth removing
the miscue and seeing whether the behaviour changes.

Scope: all three "underlying distribution" questions -- the sky provenance one
(`distribution-image + list)`) and the two contour ones (`distribution-color`,
`distribution-x/y`).  None of them is a calculation, so all three carry the
same miscue, and all three are re-asked so the answers match the wording that
produced them.

Steps (run in order; each is idempotent)
----------------------------------------
  source  patch models/utils/{plot_qa_utils,sky_plot_qa_utils}.py so newly
          generated datasets omit the clause
  jsons   rewrite the stored format string in every VQA_full qa json
  rerun   re-ask ONLY this question, per model, for the runs named by --runs,
          splicing the new answer into the existing pickles

Nothing is written without --apply.  The rerun step backs up each pickle to
<name>_qa.pickle.preclause before touching it, so the original answers remain.

    python misc/fix_provenance_question.py --step source --apply
    python misc/fix_provenance_question.py --step jsons  --apply
    python misc/fix_provenance_question.py --step rerun  --apply
    python misc/fix_provenance_question.py --step all    --apply
"""

import argparse
import ast
import glob
import json
import os
import pickle
import shutil
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, 'models'))

VQA_JSONS = os.path.expanduser('~/astro_sky_image_vqa/VQA_full/qa_jsons/')
RUN_DIRS = {
    'original':      os.path.expanduser('~/astro_sky_image_vqa/LMM_outputs_n150/'),
    'archive_light': os.path.expanduser('~/astro_sky_image_vqa/LMM_outputs_n150_archive_light/'),
    'archive':       os.path.expanduser('~/astro_sky_image_vqa/LMM_outputs_n150_archive/'),
}
# The image each run actually sent.  The aged runs keep their degraded copies
# in aged_imgs/ -- re-asking must reuse those exact files, not re-age from the
# clean original, or the answer would be to a different image than the rest of
# that run saw.
IMG_DIRS = {
    'original':      os.path.expanduser('~/astro_sky_image_vqa/VQA_full/imgs/'),
    'archive_light': os.path.expanduser('~/astro_sky_image_vqa/LMM_outputs_n150_archive_light/aged_imgs/'),
    'archive':       os.path.expanduser('~/astro_sky_image_vqa/LMM_outputs_n150_archive/aged_imgs/'),
}

# keys under VQA['Level 3']['Plot-level questions'] carrying the clause
SKY_KEY = 'distribution-image + list)'
DIST_KEYS = ('distribution-image + list)',      # sky: gmm vs real cutout
             'distribution-color + list)',      # contour: along the colour axis
             'distribution-x/y + list)')        # contour: in the x/y plane
CLAUSE = ', calculated from the data values used to create the plot'
# the question text, for locating the entry inside a run pickle
Q_MARK = 'underlying distribution'
Q_EXCLUDE = 'color-axis'          # the contour colour variant
Q_EXCLUDE2 = 'x/y-plane'          # the contour x/y variant

BACKUP_SUFFIX = '.preclause'


# --------------------------------------------------------------- step: source
def step_source(apply):
    """Teach the generator to omit the clause for the sky question only."""
    edits = []

    p = os.path.join(REPO, 'models', 'utils', 'plot_qa_utils.py')
    s = open(p).read()
    old_sig = ("def what_is_relationship(big_tag, nplots=1, axis='x', val_type='a float', \n"
               "                         use_words=True, along_an_axis=False, \n"
               "                         for_each='', use_list=False):")
    new_sig = ("def what_is_relationship(big_tag, nplots=1, axis='x', val_type='a float', \n"
               "                         use_words=True, along_an_axis=False, \n"
               "                         for_each='', use_list=False, calc_clause=True):")
    old_fmt = ("""    format = 'Please format the output as a json as {"'+big_tag+axis + '":'+outputf+'} '+panel_phrase(nplots, 'for')+', where the "'+big_tag+axis +'" value should be '+val_type+', calculated from the '
    format += 'data values used to create the plot'+for_each+'.'
    return q, adder, format""")
    new_fmt = ("""    format = 'Please format the output as a json as {"'+big_tag+axis + '":'+outputf+'} '+panel_phrase(nplots, 'for')+', where the "'+big_tag+axis +'" value should be '+val_type
    # calc_clause : the numeric questions genuinely are calculated from the
    # data, so they keep the clause.  The sky provenance question is not a
    # calculation -- it asks where the image came from -- and the phrasing
    # pushed models toward reading it as being about the pixel distribution.
    if calc_clause:
        format += ', calculated from the data values used to create the plot'+for_each+'.'
    else:
        format += '.'
    return q, adder, format""")
    if old_sig in s and old_fmt in s:
        s = s.replace(old_sig, new_sig).replace(old_fmt, new_fmt)
        edits.append((p, s))
    elif 'calc_clause' in s:
        print('  plot_qa_utils.py already patched')
    else:
        raise SystemExit('  [ERROR] plot_qa_utils.py does not match the expected text')

    p2 = os.path.join(REPO, 'models', 'utils', 'sky_plot_qa_utils.py')
    s2 = open(p2).read()
    old_call = """    text_question, adder, text_format = what_is_relationship(big_tag, nplots=nplots,"""
    new_call = """    # calc_clause=False: this asks for a judgement, not a calculation
    text_question, adder, text_format = what_is_relationship(big_tag, nplots=nplots,
                                                             calc_clause=False,"""
    if 'calc_clause' in s2:
        print('  sky_plot_qa_utils.py already patched')
    elif old_call in s2:
        s2 = s2.replace(old_call, new_call, 1)
        edits.append((p2, s2))
    else:
        raise SystemExit('  [ERROR] sky_plot_qa_utils.py does not match the expected text')

    p3 = os.path.join(REPO, 'models', 'utils', 'contour_plot_qa_utils.py')
    s3 = open(p3).read()
    if 'calc_clause' in s3:
        print('  contour_plot_qa_utils.py already patched')
    elif old_call in s3:
        s3 = s3.replace(old_call, new_call, 1)
        edits.append((p3, s3))
    else:
        raise SystemExit('  [ERROR] contour_plot_qa_utils.py does not match')

    for path, content in edits:
        print('  %s %s' % ('rewriting' if apply else 'would rewrite', path))
        if apply:
            open(path, 'w').write(content)
    if apply and edits:
        import ast
        for path, _ in edits:
            ast.parse(open(path).read())
        print('  all patched files parse')
    return len(edits)


# ---------------------------------------------------------------- step: jsons
def step_jsons(apply):
    """Strip the clause from the stored format string in every released json."""
    files = sorted(glob.glob(os.path.join(VQA_JSONS, '*_qa.json')))
    touched = skipped = 0
    for f in files:
        raw = json.load(open(f))
        d = json.loads(raw) if isinstance(raw, str) else raw
        pl = (d.get('VQA', {}).get('Level 3', {}).get('Plot-level questions', {}))
        nodes = [pl[k] for k in DIST_KEYS if k in pl]
        if not nodes:
            skipped += 1
            continue
        changed = False
        for node in nodes:
            for plot_key, entry in node.items():
                fmt = entry.get('format') or ''
                if CLAUSE in fmt:
                    entry['format'] = fmt.replace(CLAUSE, '').replace(' .', '.')
                    if not entry['format'].rstrip().endswith('.'):
                        entry['format'] = entry['format'].rstrip() + '.'
                    changed = True
        if changed:
            touched += 1
            if apply:
                # written back in the same double-encoded shape it was read in
                out = json.dumps(d) if isinstance(raw, str) else d
                with open(f, 'w') as fh:
                    json.dump(out, fh)
    print('  %d jsons scanned | %d %s | %d had no distribution question'
          % (len(files), touched, 'updated' if apply else 'would be updated', skipped))
    return touched


# ---------------------------------------------------------------- step: rerun
def _is_distribution_q(entry):
    """Any of the three 'underlying distribution' questions."""
    return Q_MARK in (entry.get('question') or '').lower()


def _load_sender(model_dir):
    """
    The notebook's own send_to_* function, plus its client.

    Imported out of the notebook rather than reimplemented so the re-asked
    question travels exactly the path the original answers did -- same retry
    logic, same image handling, same model id.
    """
    import re
    nb_name = {'chatgpt_api': 'chatgpt_withapi_test.ipynb',
               'gemini': 'gemini_withapi_test.ipynb',
               'claude_haiku': 'claude_withapi_test.ipynb'}[model_dir]
    nb_path = os.path.join(REPO, 'models', 'test_models', nb_name)
    nb = json.load(open(nb_path))
    cells = [''.join(c['source']) for c in nb['cells'] if c['cell_type'] == 'code']

    fn_name = {'chatgpt_api': 'send_to_chatgpt', 'gemini': 'send_to_gemini',
               'claude_haiku': 'send_to_claude'}[model_dir]

    g = {'__name__': '__main__'}
    cwd = os.getcwd()
    os.chdir(os.path.join(REPO, 'models', 'test_models'))
    try:
        # Run the setup cells, SKIPPING any that would start asking questions,
        # and stop as soon as the sender and the client both exist.
        #
        # Not "stop at the first run loop": the three notebooks are laid out
        # differently, and in two of them a run loop sits BETWEEN the client
        # cell and the sender definition (gemini client@3 loop@5 sender@6;
        # claude client@3 loop@4 sender@5).  Halting at the first loop leaves
        # the sender undefined.
        for src in cells:
            if fn_name in g and 'client' in g:
                break
            try:
                node = ast.parse(src)
            except SyntaxError:
                continue
            # Keep only DECLARATIVE statements -- imports, assignments, defs,
            # and the with/try blocks that read the key file.  Bare expression
            # statements and loops are dropped.
            #
            # This matters: the cell that defines the sender also CALLS it at
            # the bottom as a smoke test, so simply exec'ing the cell fires a
            # real API request just to get the function.  Filtering the tree
            # gets the definition without the side effect, and is robust to
            # the three notebooks laying their cells out differently.
            keep = (ast.Import, ast.ImportFrom, ast.Assign, ast.AnnAssign,
                    ast.AugAssign, ast.FunctionDef, ast.AsyncFunctionDef,
                    ast.ClassDef, ast.With, ast.Try, ast.If)
            node.body = [n for n in node.body if isinstance(n, keep)]
            if not node.body:
                continue
            try:
                exec(compile(node, '<nb>', 'exec'), g)
            except Exception as e:
                print('     [warn] setup cell skipped (%s: %s)'
                      % (type(e).__name__, str(e)[:60]))
    finally:
        os.chdir(cwd)
    if fn_name not in g or 'client' not in g:
        raise RuntimeError('could not load %s / client from %s' % (fn_name, nb_name))
    return g[fn_name], g['client'], g


def step_rerun(apply, runs, models, limit=None, sleep=0.0, ids=None):
    from utils.llm_utils import load_image
    total_new = 0
    for run in runs:
        run_dir = RUN_DIRS[run]
        img_dir = IMG_DIRS[run]
        if not os.path.isdir(run_dir):
            print('  [skip] no run dir: %s' % run_dir); continue
        for mdir in models:
            pkls = sorted(glob.glob(os.path.join(run_dir, mdir, '*_qa.pickle')))
            if not pkls:
                print('  [skip] no pickles: %s/%s' % (run, mdir)); continue
            targets = []
            for fp in pkls:
                payload = pickle.load(open(fp, 'rb'))
                qa = payload[0] if isinstance(payload, (list, tuple)) else payload
                if any(_is_distribution_q(e) for e in qa):
                    targets.append(fp)
            if ids:
                want = set(ids)
                targets = [t for t in targets
                           if os.path.basename(t).removesuffix('_qa.pickle') in want]
            if limit:
                targets = targets[:limit]
            print('  %-14s %-13s %d figures carry the question'
                  % (run, mdir, len(targets)))
            if not apply:
                continue

            send, client, g = _load_sender(mdir)
            for n, fp in enumerate(targets, 1):
                vqa_id = os.path.basename(fp).removesuffix('_qa.pickle')
                payload = pickle.load(open(fp, 'rb'))
                qa = payload[0] if isinstance(payload, (list, tuple)) else payload

                # the updated wording, straight from the released json, keyed
                # by question text so each of the three gets its own format
                raw = json.load(open(os.path.join(VQA_JSONS, vqa_id + '_qa.json')))
                d = json.loads(raw) if isinstance(raw, str) else raw
                pl = d['VQA']['Level 3']['Plot-level questions']
                newfmt_by_q = {}
                for k in DIST_KEYS:
                    for entry_j in pl.get(k, {}).values():
                        newfmt_by_q[(entry_j.get('question') or '').strip()] = entry_j['format']

                img = os.path.join(img_dir, vqa_id + '.jpeg')
                if not os.path.exists(img):
                    print('     [warn] no image for %s' % vqa_id); continue

                if not os.path.exists(fp + BACKUP_SUFFIX):
                    shutil.copyfile(fp, fp + BACKUP_SUFFIX)

                for e in qa:
                    if not _is_distribution_q(e):
                        continue
                    nf = newfmt_by_q.get((e.get('question') or '').strip())
                    if nf is None:
                        print('     [warn] no updated format for: %s'
                              % (e.get('question') or '')[:60])
                        continue
                    e['format'] = nf
                    try:
                        out = _ask(send, mdir, e, client, img, g)
                    except Exception as ex:
                        print('     [warn] %s failed: %s' % (vqa_id, ex)); continue
                    if out is not None:
                        e['Response'] = out
                        e['raw answer'] = out
                        e['Response String'] = out
                        e['reasked'] = True
                        total_new += 1
                with open(fp, 'wb') as fh:
                    pickle.dump(payload, fh)
                if n % 10 == 0:
                    print('     %d/%d' % (n, len(targets)))
                if sleep:
                    time.sleep(sleep)
    print('  %d answers re-collected' % total_new)
    return total_new


def _ask(send, mdir, entry, client, img_path, g):
    """
    Call the notebook's sender for one question, with THAT notebook's settings
    rather than the function defaults.

    The defaults are not what the runs used, and the gap is not cosmetic:
    send_to_claude defaults to max_tokens=1000 with thinking on at 8000 budget
    tokens, which the API rejects outright ("max_tokens must be greater than
    thinking.budget_tokens").  The notebook sets max_tokens=2000 and
    thinking=False.  Reading the values out of the notebook namespace `g` keeps
    the re-ask on the same settings as the answers it replaces, and means a
    later change in the notebook carries over here rather than silently
    diverging.
    """
    from utils.llm_utils import load_image
    ql = {k: entry.get(k, '') for k in ('persona', 'context', 'question', 'format')}
    reasoning = entry.get('reasoning')

    def cfg(name, default):
        v = g.get(name, default)
        return default if v is None else v

    if mdir == 'gemini':
        r = send(ql, img_path, client,
                 test_run=False, verbose=False,
                 img_format=cfg('img_format', 'jpeg'),
                 system_prompt=g.get('system_prompt'),
                 config=g.get('config'),
                 model_name=cfg('model_name', 'gemini-3.5-flash-lite'),
                 thinking_level=g.get('thinking_level'),
                 reasoning=reasoning)
    else:
        img_fmt = cfg('img_format_media', cfg('img_format', 'jpeg'))
        enc = load_image(img_path, img_format=img_fmt)
        if isinstance(enc, tuple):
            enc = enc[0]
        kw = dict(test_run=False, verbose=False, img_format=img_fmt,
                  reasoning=reasoning)
        if mdir == 'claude_haiku':
            kw.update(model=cfg('model', 'claude-haiku-4-5'),
                      max_tokens=cfg('max_tokens', 2000),
                      temperature=cfg('temperature', 0.1),
                      thinking=cfg('thinking', False),
                      system_prompt=g.get('system_prompt'))
        else:
            kw.update(model=cfg('model', 'gpt-5.4-nano-2026-03-17'),
                      temperature=cfg('temperature', 1.0),
                      reasoning_level=g.get('reasoning_level'),
                      verbosity=g.get('verbosity'))
        r = send(ql, client, img_path, enc, **kw)
    if isinstance(r, (list, tuple)):
        r = r[0]
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--step', default='all',
                    choices=('source', 'jsons', 'rerun', 'all'))
    ap.add_argument('--runs', default='original,archive_light',
                    help='comma-separated: original, archive_light, archive')
    ap.add_argument('--models', default='chatgpt_api,gemini,claude_haiku')
    ap.add_argument('--limit', type=int, default=0,
                    help='only this many figures per model -- for a trial run')
    ap.add_argument('--ids', default=None,
                    help='comma-separated vqa ids to restrict to, e.g. for a '
                         'trial that deliberately covers one real sky and one '
                         'synthetic sky rather than whatever sorts first')
    ap.add_argument('--sleep', type=float, default=0.0)
    ap.add_argument('--apply', action='store_true')
    a = ap.parse_args()

    runs = [r.strip() for r in a.runs.split(',') if r.strip()]
    models = [m.strip() for m in a.models.split(',') if m.strip()]
    steps = ('source', 'jsons', 'rerun') if a.step == 'all' else (a.step,)

    print('fix_provenance_question  (%s)' % ('APPLY' if a.apply else 'DRY RUN'))
    print('  runs   : %s' % ', '.join(runs))
    print('  models : %s' % ', '.join(models))
    print()
    for s in steps:
        print('--- step: %s ---' % s)
        if s == 'source':
            step_source(a.apply)
        elif s == 'jsons':
            step_jsons(a.apply)
        else:
            step_rerun(a.apply, runs, models, a.limit or None, a.sleep,
                       ids=[i.strip() for i in a.ids.split(',')] if a.ids else None)
        print()
    if not a.apply:
        print('DRY RUN -- nothing written.  Re-run with --apply.')


if __name__ == '__main__':
    main()
