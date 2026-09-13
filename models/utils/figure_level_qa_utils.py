from .plot_qa_utils import get_nplots, persona, context, get_adder


# How many panels in the figure?
def figure_qa_how_many_panels(data, qa_pairs, return_qa=True, verbose=True,
                              #use_words=True, 
                               #single_figure_flag=True, 
                               text_persona = None):

    #nplots = get_nplots(data)
    outtag = 'rows/columns'

    ### persona of assistant
    text_persona = persona(text=text_persona)
    # context for question
    text_context = '' # full figure

    text_question = 'How many panels are in this figure?'
    text_format = 'Please format the output as a json as {"nrows":"", "ncols":""} to store the number of rows and columns.'
    a1 = {"nrows":data['figure']['nrows'], "ncols":data['figure']['ncols']}
    q = text_persona + " " + text_context + " " + text_question + " " + text_format
    if verbose:
        print('QUESTION:', q)
        print('ANSWER:', a1)
        print('')
    # add to pairs
    if return_qa: 
        qa_pairs['Level 1']['Figure-level questions'][outtag] = {'Q':q, 'A':a1, 
                                                                         'persona':text_persona, 
                                                                         'context':text_context, # context nothing for full figure
                                                                         'question':text_question,
                                                                         'format':text_format}
        return qa_pairs
    


# plotting style
def figure_qa_plotting_style(data, qa_pairs, return_qa=True, verbose=True,
                              #use_words=True, 
                               #single_figure_flag=True, 
                               text_persona = None):
    outtag = 'plot style'

    ### persona of assistant
    text_persona = persona(text=text_persona)
    # context for question -- was accidentally repeated!
#    text_context = 'Assume this is a figure made with matplotlib in Python.  Examples of plotting styles are "classic" or "ggplot". Examples of plotting styles are "classic" or "ggplot".' # full figure but context
    text_context = 'Assume this is a figure made with matplotlib in Python.  Examples of plotting styles are "classic" or "ggplot".' # full figure but context

    text_question = 'What is the plot style used in this figure?'
    text_format = 'Please format the output as a json as {"plot style":""} to store the matplotlib plotting style used in the figure.'
    answer = {"plot style":data['figure']['plot style']}
    q = text_persona + " " + text_context + " " + text_question + " " + text_format
    if verbose:
        print('QUESTION:', q)
        print('ANSWER:', answer)
        print('')
    # add to pairs
    if return_qa: 
        qa_pairs['Level 1']['Figure-level questions'][outtag] = {'Q':q, 'A':answer, 
                                                                         'persona':text_persona, 
                                                                         'context':text_context, # context nothing for full figure
                                                                         'question':text_question,
                                                                         'format':text_format}
        return qa_pairs




# Colormaps?
def figure_qa_colormap(data, qa_pairs, return_qa=True, verbose=True, 
                       text_persona = None):
    
    outtag = 'colormap'
    
    ### persona of assistant
    text_persona = persona(text=text_persona)
    # context for question
    text_context = 'Assume this is a figure made with matplotlib in Python. Examples of matplotlib colormaps are "rainbow" or "Reds".' # full figure but context

    text_question = 'What is the colormap that was used in this figure?'
    text_format = 'Please format the output as a json as {"colormap":""} to store the matplotlib colormap used in the figure.'
    answer = {"colormap":data['figure']['color map']}
    q = text_persona + " " + text_context + " " + text_question + " " + text_format
    if verbose:
        print('QUESTION:', q)
        print('ANSWER:', answer)
        print('')
    # add to pairs
    if return_qa: 
        qa_pairs['Level 1']['Figure-level questions'][outtag] = {'Q':q, 'A':answer, 
                                                                         'persona':text_persona, 
                                                                         'context':text_context, # context nothing for full figure
                                                                         'question':text_question,
                                                                         'format':text_format, 
                                                                         'notes':"Some of the plot styles don't allow for updates to the colormap for REASONS, so just keep that in mind."}
        return qa_pairs
    

# aspect ratio
def figure_qa_aspect_ratio(data, qa_pairs, return_qa=True, verbose=True, 
                       text_persona = None):
    
    outtag = 'aspect ratio'
    ### persona of assistant
    text_persona = persona(text=text_persona)
    # context for question
    text_context = '' # full figure

    text_question = 'What is the aspect ratio of this figure?'
    #text_format = 'You are a helpful assistant, please format the output as a json as {"aspect ratio":""} to store the aspect ratio of the plot.' # JPN also
    text_format = 'Please format the output as a json as {"aspect ratio":""} to store the aspect ratio of the plot.' # JPN also update
    answer = {"aspect ratio":data['figure']['aspect ratio']}
    q = text_persona + " " + text_context + " " + text_question + " " + text_format
    if verbose:
        print('QUESTION:', q)
        print('ANSWER:', answer)
        print('')    

    if return_qa: 
        qa_pairs['Level 1']['Figure-level questions'][outtag] = {'Q':q, 'A':answer, 
                                                                         'persona':text_persona, 
                                                                         'context':text_context, 
                                                                         'question':text_question,
                                                                         'format':text_format}
        return qa_pairs



############ INDIVIDUAL PLOTS IN GENERAL ##############

def q_plot_titles(data, qa_pairs, return_qa=True, verbose=True, 
                  text_persona = None):
    outtag = 'titles'
    ### persona of assistant
    text_persona = persona(text=text_persona)
    ### context for question
    text_context = '' # full figure

    text_question = 'What are the titles for each figure panel?'
    text_format = 'Please format the output as a json as {"titles":[]}, where the list is a list of strings of all of the titles. '
    text_format += 'If there is a single plot, this should be one element in this list, and if there are multiple plots the list should be in row-major (C-style) order.'
    text_format += " If a plot does not have a title, then denote this by an empty string in the list.  Please format any formulas in the title in a Python LaTeX string (for example 'Light $\\\\alpha$'). "

    la = []
    for k,v in data.items():
        if 'plot' in k: # is a plot
            if 'title' not in v:
                la.append("")
            else:
                la.append(v['title']['words'])
    answer = {"titles":la} # JPN also updated so both say "titles"

    q = text_persona + " " + text_context + " " + text_question + " " + text_format
    if verbose:
        print('QUESTION:', q)
        print('ANSWER:', answer)
        print('')  

    if return_qa: 
        qa_pairs['Level 1']['Figure-level questions'][outtag] = {'Q':q, 'A':answer, 
                                                                         'persona':text_persona, 
                                                                         'context':text_context, 
                                                                         'question':text_question,
                                                                         'format':text_format}
        return qa_pairs


def q_plot_axis_labels(data, qa_pairs, return_qa=True, verbose=True, 
                   text_persona=None, axis='x'):
    outtag = axis + 'labels'
    ### persona of assistant
    text_persona = persona(text=text_persona)
    ### context for question
    text_context = '' # full figure
    ### question
    text_question = 'What are the '+axis+'-axis titles for each figure panel?' # JPN update
    text_format = 'Please format the output as a json as {"'+axis+'labels":[]}, where the list is a list of strings of all of the '+axis+'-axis titles. '
    text_format += 'If there is a single plot, this should be one element in this list, and if there are multiple plots the list should be in row-major (C-style) order.'
    text_format += " If a plot does not have an "+axis+"-axis title, then denote this by an empty string in the list.  "
    text_format += "Please format any formulas in the title in a Python LaTeX string (for example 'Light $\\\\alpha$'). "
    ### all together
    q = text_persona + " " + text_context + " " + text_question + " " + text_format
    ### labels
    la = []
    for k,v in data.items():
        if 'plot' in k: # is a plot
            if axis+'label' not in v:
                la.append("")
            else:
                la.append(v[axis+'label']['words'])
    answer = {axis+"labels":la}
    if verbose:
        print('QUESTION:', q)
        print('ANSWER:', answer)
    if return_qa: 
        qa_pairs['Level 1']['Figure-level questions'][outtag] = {'Q':q, 'A':answer, 
                                                                         'persona':text_persona, 
                                                                         'context':text_context, 
                                                                         'question':text_question,
                                                                         'format':text_format}
        return qa_pairs
    

def q_ticklabels(data, qa_pairs, axis='x', return_qa=True, verbose=True, text_persona=None):
    outtag = axis + 'tick values'
    ### persona of assistant
    text_persona = persona(text=text_persona)
    ### context for question
    text_context = '' # full figure
    text_question = 'What are the values for each of the tick marks on the '+axis+'-axis?'
    ### format
    text_format = 'Please format the output as a json as {"'+axis+'tick values":[[]]}, where each element of the outer list refers to a single panel, '
    text_format += 'and each inner list is a list of the '+axis+'-axis tick mark values. '
    text_format += 'If there is a single plot, this should be one element in the outer list, and if there are multiple plots the outer list should be in row-major (C-style) order.'
    text_format += " If a plot does not have any "+axis+"-axis tick values, then denote this by an empty string in the inner list.  "
    text_format += "Please format any formulas in the "+axis+"-axis tick values in a Python LaTeX string (for example 'Light $\\\\alpha$')."
    q = text_persona + " " + text_context + " " + text_question + " " + text_format
    ### answer
    la = []
    for k,v in data.items():
        if 'plot' in k: # is a plot
            if axis+'ticks' not in v:
                la.append("")
            else:
                t = []
                for l in v[axis+'ticks']:
                    t.append(l['data'])
                la.append(t)
    answer = {axis+"tick values":la}
    if verbose:
        print('QUESTION:', q)
        print('ANSWER:', answer)
    if return_qa: 
        qa_pairs['Level 1']['Figure-level questions'][outtag] = {'Q':q, 'A':answer, 
                                                                         'persona':text_persona, 
                                                                         'context':text_context, 
                                                                         'question':text_question,
                                                                         'format':text_format}
        return qa_pairs



def q_plot_types(data, qa_pairs, plot_types, return_qa=True, use_list=True, 
                 verbose=True, text_persona=None):
    outtag = 'plot types'
    adder = '' # updated if using list
    ### persona of assistant
    text_persona = persona(text=text_persona)
    ### question
    text_question = 'What are the plot types for each panel in the figure?'
    ### context for question
    text_context = '' # full figure
    if use_list:
        adder = ' (list)'
        text_context = 'Please choose each plot type from the following list: ['
        for pt in plot_types:
            text_context += pt + ', '
        text_context = text_context[:-2] # take off the last bit
        text_context += '].'
    ### format
    text_format = 'Please format the output as a json as {"plot types":[]}, where each element of the list refers to the plot type of a single panel. '
    text_format += 'If there is a single plot, this should be one element in this list, and if there are multiple plots the list should be in row-major (C-style) order. '
    # full q
    q = text_persona + " " + text_context + " " + text_question + " " + text_format

    la = []
    for k,v in data.items():
        if 'plot' in k: # is a plot
            if 'type' not in v:
                la.append("")
            else:
                la.append(v['type'])
    answer = {"plot types":la}
    if verbose:
        print('QUESTION:', q)
        print('ANSWER:', answer)
    if return_qa: 
        qa_pairs['Level 1']['Figure-level questions'][outtag + adder] = {'Q':q, 'A':answer, 
                                                                         'persona':text_persona, 
                                                                         'context':text_context, 
                                                                         'question':text_question,
                                                                         'format':text_format}
        return qa_pairs




#import .general_plot_level_qa_utils
#reload(utils.general_plot_level_qa_utils)
from .general_plot_level_qa_utils import q_errorbars_existance_lines

def figure_level_qa(data, qa_pairs, plot_types, verbose=False):
    ######## FIGURE LEVEL, L1 ########
    qa_pairs = figure_qa_how_many_panels(data, qa_pairs, verbose=verbose)
    qa_pairs = figure_qa_plotting_style(data, qa_pairs, verbose=verbose)
    qa_pairs = figure_qa_colormap(data, qa_pairs, verbose=verbose)
    qa_pairs = figure_qa_aspect_ratio(data, qa_pairs, verbose=verbose)
    # basic, plot level in general
    qa_pairs = q_plot_titles(data, qa_pairs, verbose=verbose)
    qa_pairs = q_plot_axis_labels(data, qa_pairs, axis='x', verbose=verbose)
    qa_pairs = q_plot_axis_labels(data, qa_pairs, axis='y', verbose=verbose)
    qa_pairs = q_ticklabels(data, qa_pairs, axis='x', verbose=verbose)
    qa_pairs = q_ticklabels(data, qa_pairs, axis='y', verbose=verbose)
    qa_pairs = q_plot_types(data, qa_pairs, plot_types, use_list=True, verbose=verbose)
    qa_pairs = q_plot_types(data, qa_pairs, plot_types, use_list=False, verbose=verbose)
    return qa_pairs