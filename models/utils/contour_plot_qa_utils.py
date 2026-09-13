import numpy as np

### JPN -- these all need to be cleaned!



from .plot_qa_utils import get_nplots, persona, context_single_multi, how_many, how_much_data_values, get_format_adder#, get_adder




####### CONSTRUCT QUESTIONS ########

####### L1 #######
# contour plot, with lines, or just image?
# this version tries to give column and row numbers
def q_contour_plot_image_or_lines(data, qa_pairs, plot_num = [0,0], 
                               return_qa=True, verbose=True, use_words=True, use_list=True,
                               single_figure_flag=True, 
                               text_persona = None, level='Level 1'):
    """
    Construct Q/A for how many lines are in the plot.
    """
    big_tag = 'image or lines'
    object = 'contour plot'
    # get answer
    itag = ''
    for d,v in data['plot'+str(plot_num)]['data from plot']['data'].items():
        itag += d
    if 'image' in itag and 'contour' in itag:
        ans = 'both'
    elif 'image' in itag:
        ans = 'image'
    elif 'contour' in itag: # just contour lines
        ans = 'contour lines'
    else:
        print('dont know what this contour plot type is!')
        import sys; sys.exit()
    
    #--- typically don't need to change below ----

    nplots = get_nplots(data)

    ### persona of assistant
    text_persona = persona(text=text_persona)
    ## context for question
    text_context = context_single_multi(data, nplots, plot_num, use_words, single_figure_flag)

    ### question, format of output
    adder, text_format = get_format_adder(object, big_tag, 
                                                       val_type = 'a string', 
                                                       nplots = nplots, 
                                                       use_words=use_words,
                                                       use_list=use_list)
    # basic question
    text_question = 'What is the style of the ' + object + '?'
    if use_list:
        text_question += ' Please choose the style from the following list: [image, contour lines, both].'
    # construct question:
    q = text_persona + " " + text_context + " " + text_question + " " + text_format
    # get answer, formatted
    a = {big_tag + adder: ans}
    if verbose:
        print('QUESTION:', q)
        print('ANSWER:', a)
    if return_qa: 
        if big_tag + adder not in qa_pairs[level]['Plot-level questions']:
            qa_pairs[level]['Plot-level questions'][big_tag +  adder] = {'plot'+str(plot_num):{'Q':q, 'A':a, 
                                                                                                        'persona':text_persona, 
                                                                                                        'context':text_context,
                                                                                                        'question':text_question, 
                                                                                                        'format':text_format}}
        else:
            qa_pairs[level]['Plot-level questions'][big_tag + adder]['plot'+str(plot_num)] = {'Q':q, 'A':a, 
                                                                                                        'persona':text_persona, 
                                                                                                        'context':text_context,
                                                                                                        'question':text_question, 
                                                                                                        'format':text_format}
        return qa_pairs
    

## JPN: come back, number of levels?

def q_stats_contours(data, qa_pairs, stat = {'minimum':np.min}, axis = 'x',
                  plot_num = 0, 
                     return_qa=True, use_words=True, verbose=True, 
                     single_figure_flag=True, 
                               text_persona = None):
    """
    stat: {'name':stat} which gives name of stat and function to calculate it, like {'minimum':np.min}
    use_words : set to True to translate row, column to words; False will use C-ordering indexing
    stat : dictionary of the name and function to use for each stat
    """
    # output type
    val_type = 'a float'

    # check
    if axis.lower() == 'x': 
        axis = 'x'
    elif axis.lower() == 'y':
        axis = 'y'
    elif axis.lower() == 'color':
        axis = 'color'
    else:
        print('Axis not chosen correctly:', axis)
        import sys; sys.exit()

    #### Answer
    f = list(stat.values())[0] # what statical function
    zs = data['plot'+str(plot_num)]['data'][axis+'s']
    for_each = ''
    list_stat = f(zs)

    #---- Don't have to change much below ----
    big_tag = list(stat.keys())[0]
    # get nplots    
    nplots = get_nplots(data)

    ### persona of assistant
    text_persona = persona(text=text_persona)
    ## context for question
    text_context = context_single_multi(data, nplots, plot_num, use_words, single_figure_flag)

    text_question, adder, text_format  = how_much_data_values(big_tag, nplots=nplots, 
                                                              axis=axis, 
                                                              val_type=val_type, 
                                                              use_words=use_words, 
                                                              along_an_axis=True,
                                                              for_each=for_each)
    # big tag update
    big_tag += ' ' + axis
    # format answer
    #la = {big_tag + " "+axis:list_stat}
    la = {big_tag:list_stat}
    ans = {big_tag +  adder:{'plot'+str(plot_num):la}} 
    a = {big_tag +  adder:la}
    # construct question:
    q = text_persona + " " + text_context + " " + text_question + " " + text_format

    if verbose:
        print('QUESTION:', q)
        print('ANSWER:', ans)
    if return_qa: 
        if big_tag + adder not in qa_pairs['Level 2']['Plot-level questions']:
            qa_pairs['Level 2']['Plot-level questions'][big_tag + adder] = {'plot'+str(plot_num):{'Q':q, 'A':a, 
                                                                                                        'persona':text_persona, 
                                                                                                        'context':text_context,
                                                                                                        'question':text_question, 
                                                                                                        'format':text_format}}
        else:
            qa_pairs['Level 2']['Plot-level questions'][big_tag + adder]['plot'+str(plot_num)] = {'Q':q, 'A':a, 
                                                                                                        'persona':text_persona, 
                                                                                                        'context':text_context,
                                                                                                        'question':text_question, 
                                                                                                        'format':text_format}
        return qa_pairs
    



########## L2/L3 #############
from .plot_qa_utils import what_is_relationship
def q_relationship_contour(data, qa_pairs, plot_num = 0, axis='color',
                         return_qa=True, use_words=True, 
                         use_list=True, 
                        line_list = ['random','linear','gaussian mixture model'], 
                        single_figure_flag=True,
                        verbose=True, text_persona = None):
    """
    use_words : set to True to translate row, column to words; False will use C-ordering indexing
    use_list : give a list of possible distributions
    use_nplots : give the number of lines in the prompt

    axis : can be 'color' or 'x/y'
    """
    
    # how many plots
    big_tag = 'distribution'
    val_type = 'a string'
    for_each = ''
    along_an_axis = True
    if (axis != 'color') and (axis !='x/y'):
        print('wrong selection for axis!  must be "color" or "x/y"')
        import sys; sys.exit()
    mark = 'scatter'
    #big_tag += '-' + axis

    ### answer
    dist = data['plot'+str(plot_num)]['distribution']
    # to match
    if dist == 'gmm': dist = 'gaussian mixture model'
    la = dist

    # ---- don't have to change much below this -----
    # get nplots    
    nplots = get_nplots(data)
    #adder = get_adder(nplots, use_words)
    text_question, adder, text_format = what_is_relationship(big_tag, nplots=nplots, 
                                                              val_type=val_type, 
                                                              use_words=use_words, 
                                                              along_an_axis=along_an_axis,
                                                              axis=axis,
                                                              for_each=for_each)
    
    ### persona of assistant
    text_persona = persona(text=text_persona)
    ## context for question
    text_context = context_single_multi(data, nplots, plot_num, use_words, single_figure_flag)

    text_context_adder = ''
    if use_list:
        adder = adder.split(')')[0] + ' + list)'
        if for_each != '':
            fe = ' for each '+mark
            eot = 'each'
        else:
            fe = ''
            eot = 'the'
        text_context_adder += ' Please choose '+eot+' '+big_tag+fe+' from the following list: ['
        for pt in line_list:
            text_context_adder += pt + ', '
        text_context_adder = text_context_adder[:-2] # take off the last bit
        text_context_adder += '].'
    text_context += text_context_adder

    q = text_persona + " " + text_context + " " + text_question + " " + text_format

    a = {big_tag + adder:la}

    if verbose:
        print('QUESTION:', q)
        print('ANSWER:', a)
    if return_qa: 
        if big_tag + '-' + axis + adder not in qa_pairs['Level 3']['Plot-level questions']:
            qa_pairs['Level 3']['Plot-level questions'][big_tag + '-' + axis + adder] = {'plot'+str(plot_num):{'Q':q, 'A':a, 
                                                                                                              'note':'this currently assumes all elements on a single plot have the same relationship type', 
                                                                                                        'persona':text_persona, 
                                                                                                        'context':text_context,
                                                                                                        'question':text_question, 
                                                                                                        'format':text_format}}
        else:
            qa_pairs['Level 3']['Plot-level questions'][big_tag + '-' + axis + adder]['plot'+str(plot_num)] = {'Q':q, 'A':a, 
                                                                                                              'note':'this currently assumes all elements on a single plot have the same relationship type', 
                                                                                                        'persona':text_persona, 
                                                                                                        'context':text_context,
                                                                                                        'question':text_question, 
                                                                                                        'format':text_format}
        return qa_pairs
    
   

