import numpy as np
from PIL import Image
import base64
import json
import os
import re

# parsing
def parse_qa(level_parse, plot_level, qa, j, types, 
             partials = ['persona', 'context','question', 'format'], 
             use_split_keys = True):
    keys_tmp = list(j[level_parse][plot_level].keys())
    keys = []
    for k in keys_tmp:
        if '(' in k and use_split_keys:
            k = k.split('(')[0].rstrip()
        keys.append(k)
    
    keys = np.unique(keys).tolist()

    dirs_partials = {}
    
    for k in keys:
        v = ''
        kk = ''
        for t in types:
            if k + " " + t in j[level_parse][plot_level]: # e.g., 'nlines (list + words)
                v = j[level_parse][plot_level][k + " " + t]
                #kk = k + " " + t
                break
        # if not use splits
        if not use_split_keys:
            if k in j[level_parse][plot_level]:
                v = j[level_parse][plot_level][k]
        if v == '':
            #print("HI")
            v = j[level_parse][plot_level][k]
            #kk = k
            # get other elements
            #print(v)
            for p in partials:
                dirs_partials[p] = v[p]
        if 'A' in v: # no plot
            #print("HI2")
            if type(v['A']) == type({}):
                ans = list(v['A'].values())[0]
            else:
                ans = v['A']
            if type(v['Q']) == type({}):
                que = list(v['Q'].values())[0]
            else:
                que = v['Q']
            # get other elements
            for p in partials:
                dirs_partials[p] = v[p]
        else: # plotX
            #print("HI3")
            #print('v=', v)
            for kk,vv in v.items(): # kk=plotX,stuff
                #print('kk,vv', kk,vv)
                ans = vv['A']
                while type(ans) == type({}):
                    ans_1 = list(ans.values())[0]
                    if 'plot' in list(ans.keys())[0]:
                        ans = ans_1
                        break
                    ans = ans_1
                que = vv['Q']
                #print('ans, q', ans, que)
                # get other elements
                for p in partials:
                    dirs_partials[p] = vv[p]
                #print('dirs_partials:', dirs_partials)
        out = {'Q':que, 'A':ans, 'Level':level_parse, 'type':plot_level, 'Response':""}
        for kp,vp in dirs_partials.items():
            out[kp] = vp
        # if there is a plot
        if 'plot' in list(v.keys())[0]:
            out['plot number'] = list(v.keys())[0]
            #import sys; sys.exit()
        qa.append(out)
    return qa


def load_image(image_path, tmp_dir = '~/Downloads/tmp/', fac=1.0, 
               return_image_format = False, 
               img_format='png', 
               max_img_size=(None,None)):
    """
    Encode image for passing to various LLMs.

    img_format : the format of the encoded image
    """
    tmp_dir = os.path.expanduser(tmp_dir)
    # check options for image format
    if img_format not in ['png', 'jpeg', 'gif']:
        img_format = 'png'
    #print('1:', image_path)
    img = Image.open(image_path).convert('RGB')
    if fac != 1.0:
        new_size = np.round(np.array(img.size)*fac).astype('int')
        img = img.resize(new_size, Image.Resampling.LANCZOS)
    # test
    if max_img_size[0] is not None:
        if img.size[0] > max_img_size[0]:
            n0 = max_img_size[0]-1
            aspect = int(round(img.size[1]*float(n0)/img.size[0]))
            img = img.resize((n0,aspect), Image.Resampling.LANCZOS)
    if max_img_size[1] is not None:
        if img.size[1] > max_img_size[1]:
            n0 = max_img_size[1]-1
            aspect = int(round(img.size[0]*float(n0)/img.size[1]))
            img = img.resize((aspect,n0), Image.Resampling.LANCZOS)            
    #img = np.array(img)
    #with open(image_path, "rb") as image_file:
    img.save(tmp_dir + 'tmp_img.'+img_format)
    if not return_image_format:
        with open(tmp_dir +'tmp_img.'+img_format,'rb') as image_file:
            #return base64.b64encode(img).decode("utf-8")
            return base64.b64encode(image_file.read()).decode("utf-8")
    else:
         with open(tmp_dir +'tmp_img.'+img_format,'rb') as image_file:
            #return base64.b64encode(img).decode("utf-8")
            return base64.b64encode(image_file.read()).decode("utf-8"), img_format  


def get_img_json_pair(img_path, json_path, dir_api, 
                      tmp_dir = '~/Downloads/tmp/',
                      fac = 1.0, 
                      img_format = 'png',
                      return_image_format = True,
                      restart = False, verbose = True, 
                      load_image_tmp = True, 
               max_img_size=(None,None)):
    """
    img_path : where image file is stored
    json_path : where json path is stored
    dir_api : where we can look for prior, saved pickles, if applicable
    fac : do we want to downsize the image? IF so, set to < 1
    load_image_tmp : if set to False, doesn't load image but tries to figure out format from suffix

    returns: encoded image, full json from creation run, error
      encoded image and full json are empty strings if error is True
    """
    #print('on', iFile, 'of', iMax)
    err = False
    tmp_dir = os.path.expanduser(tmp_dir)
    base_file = json_path.split('/')[-1].removesuffix('.json')
    if dir_api is not None:
        if os.path.exists(dir_api + base_file + '.pickle') and not restart:
            if verbose: print('have file already:', dir_api + base_file + '.pickle')
            if not return_image_format:
                return '','', True
            else:
                return '', '', '', True
    # do we have it?
    try:
    #if True:
        #image_path = '/Users/jnaiman/Downloads/data_full_v2/Picture'+str(int(iFile))+'.png'
        if load_image_tmp:
            encoded_image, img_format = load_image(img_path, fac=fac, tmp_dir=tmp_dir, 
                                               img_format=img_format, 
                                               return_image_format=return_image_format, 
                                               max_img_size=max_img_size)
        else:
            encoded_image = ''
            img_format = img_path.split('.')[-1]
    except Exception as e:
    #else:
        if verbose: 
            print('[ERROR]:', str(e))
            print('  could not load image')
        err = True
        if not return_image_format:
            return '','', True
        else:
            return '', '', '', True
    try:
        # get questions
        with open(json_path,'r') as f:
            j = json.loads(f.read())
            j = json.loads(j)
    except Exception as e:
        if verbose: 
            print('[ERROR]:', str(e))
            print('json path:', json_path)
        err = True
        if not return_image_format:
            return '','', True
        else:
            return '', '', '', True
    
    return encoded_image, img_format, j, err


def parse_for_errors(qa, llm='chatgpt',
                     verbose=True, print_what = 'prompt'):
    """
    print_what : set to "prompt" to print full prompt, or "question" for just the question
    """
    # try to fix
    for level in qa:
        # if verbose:
        #     print(level)
        noErr = False
        if 'Error' in level:
            noErr = True
            try:
                iters = []
                for x in re.finditer(r'//(\s*)(.*)(\s*)\n', level['Response']):
                    #print(x)
                    iters.append(level['Response'][x.span()[0]:x.span()[1]])
                
                response = level['Response']
                for i in iters:
                    response = response.replace(i,'')
                level['Response'] = response
                del level['Error']
            except:
                noErr = False
                print('********')
                print('couldnt fix:', level['Response'])
                print('********')
                pass
    
        try:
            if type(level['Response']) != type({}):
                level['Response'] = json.loads(level['Response'])
        except:
            pass

        # double check no ````json` in there
        if '```json' in level['Response']:
            #print("HIIIIII")
            try:
                raw_ans = level['raw answer']
                level['Response'] = json.loads(raw_ans.split('```json')[-1].split('```')[0].replace('\n',''))
            except:
                print('*******')
                print('could not fix raw ans with Response')
                print('Response: ', level['Response'])
                print('Raw Answer: ', level['raw answer'])
                print('*******')
                #import sys; sys.exit()
    
        print_llm = 'LLM'
        if llm.lower()=='chatgpt':
            print_llm = 'ChatGPT'
        elif 'claude' in llm.lower():
            print_llm = 'Claude'
        elif 'gemini' in llm.lower():
            print_llm = 'Gemini'
        else:
            print_llm = llm.capitalize()
        if not noErr and verbose:
            if print_what == 'question':
                print('Q:', level['Q'])
            elif print_what == 'prompt':
                print('Q:', level['prompt'])
            print(print_llm + ' A:', level['Response'])
            print('Real A:   ', level['A'])

            print('')
            #if 'Error' in level:
            #    import sys; sys.exit()
    return qa