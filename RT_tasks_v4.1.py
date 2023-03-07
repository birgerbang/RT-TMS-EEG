"""
Simple Reaction Time (left and right), Uninformed Choice Reaction Time & Informed Choice Reaction Time tasks
Made for a TMS/EEG experiment at the University of Oslo

Written by: BirgerBang 

Made for PsychoPy-2022.2.4 © 2002-2018 Jonathan Peirce © 2019 Open Science Tools Ltd.

"""
# %% Import Necessary Packages
#from ast import main
import sys, os
from sqlite3 import Timestamp
from datetime import datetime
import numpy as np
from psychopy import visual, core, event, clock, gui, data, parallel
import PyQt5
#from psychopy.tools.filetools import fromFile, toFile
import random, csv, time, serial, math

#%%
debug = True # disables serial and parallel triggers, for testing.

############## Experiment settings ##################
tasks = ['SRT_L', 'SRT_R', 'UCRT', 'ICRT']      # a list of which tasks to be run: 'SRT_L', 'SRT_R', 'UCRT', 'ICRT'
ITI = (4000, 5000)                              # sets the range of the ITI in ms.
PCISI = (900, 900)                              # sets the range of the interval between PC and IS in ICRT (in ms).
maxRT = 1000                                    # the maximum allowd time to respons anfter IS, in ms
RTtrials = 2                                   # the number of trials used to determine mean RT for TMS at 50%RT. If set to zero
catchRatio = 0.1                                # the amount of catch trials to be added, relative to non-catch trials
trialsPerStimtimePerCondition = 1              # the number of trials for each stimulation, per hand per task. 
baselinesPerCondition = 1                       # the number of baseline EMG trials, per hand per task.
bl_before = 0                                  # Number of MEP baselines before &
bl_after = 0                                    # after the experimental tasks
enableBreaks = True                             # enables brakes for the participant to rest
breakInterval = 10*60                           # enables a break every 10th minute (600th s)

keyLeft = 'a' # For left index finger button presses
keyRight = 'g' # For right index finger button presses
keyContinue = 'd' # For user to continue (middle keypad button)

######## TMS stimulation times #################
stimTime_BL = -500                               # the time at which to stimulate with TMS for baseline EMG measurement
stimTimes_SRT_L = [-100, 'halfRT']                # the times at which to stimulate with TMS in SRT_L task, relative to imperative signal
stimTimes_SRT_R = [-100, 'halfRT']                # the times at which to stimulate with TMS in SRT_L task, relative to imperative signal
stimTimes_UCRT = [-100, 'halfRT']                 # the times at which to stimulate with TMS in UCRT task, relative to imperative signal
stimTimes_ICRT = [-100, 'halfRT']                 # the times at which to stimulate with TMS in ICRT task, relative to imperative signal

#NOTE: halfRT is in fact taskandhandspecificRT/3

############ paralell port trigger setup ############
# Set trigger duration (minimum trigger duration depend on sampling rate of EEG system: e.g. 250hz == 8ms, 500hz == 4ms, 1000hz == 2ms)
trig_wait = 0.001
# Set parallel port address
if not debug:
    para = parallel.ParallelPort(address=0x378)
    para.setData(0) #set all pins low

def sendRemark(trigger):
    if not debug:
        para.setData(trigger)
        core.wait(trig_wait)
        para.setData(0)

t_goLeft = 1
t_goRight = 2

t_SRT_gL = 11 # go left in SRT
t_SRT_gR = 12 # go right in SRT

t_UCRT_gL = 21 # go left in UCRT
t_UCRT_gR = 22 # go right in UCRT

t_ICRT_gL = 31 # go left in ICRT
t_ICRT_gR = 32 # go right in ICRT

t_pCue = 50 # preparatory cue

t_X = 8 # catch signal X
t_fixStart = 9 # fixation start
t_respL = 65 # left hand response
t_respR = 70 # right hand response
t_respError = 75 # a response which is neither right nor left. (should not happen)

t_timeout = 80 # trial timeout - if no response
t_trialEnd = 99 # end of current trial
t_TMS = 100 # TMS sent
t_startExp = 111 # start of experiment
t_startBlock = 112 # start of block
t_pause = 113 #pause

t_endExp = 255 # experiment finished


############ serial port TMS trigger setup ###########
# Set serial send period to 1ms
ser_wait = 0.001
if not debug: 
    ser = serial.Serial('COM1', baudrate = 9600, timeout = 0)

def sendTMS():
    if not debug:
        ser.write(100)
        core.wait(ser_wait)
        ser.write(0)
#########################################################

# %% Create log, info and data folders if not existing:
for folder in ['info', 'log', 'data']:
    if not os.path.exists(folder):
        os.makedirs(folder)

# %% Get info from experimenter
info = {"Observer":"BB", "ExpVersion": 2.1, "Group": ["Pilot", "Control"], "Subject ID":int(0), "Handedness" : ["Right", "Left", "Ambidextrous"], "Date and Time": str(datetime.now())[0:19], "Start from trial:":0}
infoDlg = gui.DlgFromDict(dictionary=info,
title="RT-experiment", fixed=["ExpVersion"])

if infoDlg.OK:
    print(info)
else:
    print("\nUser Cancelled")
    core.quit()

dir_path = os.path.dirname(os.path.realpath(__file__))     # Get the current directory of this script file. 
sys.stdout = open(f'{dir_path}\log\log_{info["Subject ID"]}.txt', "w") # logging of python printout

# %% Save the user inpur to a info_ID.csv file
filename = f'info_{info["Subject ID"]}'
while os.path.exists(f'{dir_path}\info\{filename}.csv'):    # ensure unique filename of info file
    filename = f'{filename}_new'
datafile = open(f'{dir_path}\info\{filename}.csv', "w")
writer = csv.writer(datafile, delimiter = ";")
writer.writerow(info.keys())
writer.writerow(info.values())
datafile.close()

# %% Open data output file
filename = f'RT_data_{info["Subject ID"]}'
while os.path.exists(f'{dir_path}\data\{filename}.csv'):    # ensure unique filename of info file
    filename = f'{filename}_new'
datafile = open(f'{dir_path}\data\{filename}.csv', "w")
writer = csv.writer(datafile, delimiter = ";")
writer.writerow (["trialnumber", "task", "right", "response", "responseTime", "correct", "tms_sent", "is_catch", "is_train", "time"]) # The collumn names in the csv file

#create a window
mywin = visual.Window([1728, 1117], monitor="testMonitor", units="deg", color= (0,0,0), fullscr = True)

# %% Defining visual stimuli for the RT tasks
fixation = visual.TextStim(win = mywin, text = '+', color = [1,1,1], contrast=5.0, height = 1.5)
# Go for SRT
SRTgoalStim = visual.ShapeStim(win = mywin, lineColor = [1,1,1], vertices = [[-0.3, 1.5], [-1.5, 1.5],[-1.5, -1.5], [-0.3,-1.5]], closeShape = False, lineWidth = 10, pos = (0, -1.5), ori = 90)
SRTgoStim = visual.Circle(win = mywin, fillColor = [1,1,1], size = [1, 1], pos = (0, -3))
# Go right and left for UCRT & ICRT
goRight = visual.Circle(win = mywin, fillColor = [1,1,1], size = [1,1], pos = (3, 0))
goLeft = visual.Circle(win = mywin, fillColor = [1,1,1], size = [1,1], pos = (-3, 0))
# right and left "Goal" for UCRT & ICRT
goalRight = visual.ShapeStim(win = mywin, lineColor = [1,1,1], vertices = [[-0.3, 1.5], [-1.5, 1.5],[-1.5, -1.5], [-0.3,-1.5]], closeShape = False, lineWidth = 10, pos = (1.75, 0))
goalLeft = visual.ShapeStim(win = mywin, lineColor = [1,1,1], vertices = [[-0.3, 1.5], [-1.5, 1.5],[-1.5, -1.5], [-0.3,-1.5]], closeShape = False, lineWidth = 10, pos = (-1.75, 0), ori = 180)
# X for catch trials 
catchX = visual.ShapeStim(win = mywin, lineColor = [1,1,1], vertices = [[-2,2], [2,-2], [0,0], [2,2], [-2,-2]], closeShape = False, lineWidth = 20)
# Just some info text
infoStim = visual.TextStim(win = mywin, text = 'Info text', color = [1,1,1], wrapWidth = 22, height = 0.8)
# Creating a global clock to keep track of time
globalTimer = core.Clock()
# Defining a visual representation of the clock, for debugging mainly
globalTimerVisual = visual.TextStim(win=mywin, text = globalTimer.getTime(), color = [1,1,1], pos = (10,-10))

# %% Defining the function to run trial and return results #################
def trialRT1(trial_N = 0, task = 'SRT', tms_time = -100, fixDur = 500, maxRT = 1000, interDur = 900, right = True, is_catch = False, halfRT_R = 150, halfRT_L = 150, is_train = False):

    ####### Setting up variables for the trial #######
    correctKey = keyRight if right else keyLeft                           # left or right response button

    # EEG-triggers #
    if task == 'ICRT':
        t_goLeft = t_ICRT_gR
        t_goRight = t_ICRT_gR
    elif task == 'UCRT':
        t_goLeft = t_UCRT_gL
        t_goRight = t_UCRT_gR
    else:
        t_goLeft = t_SRT_gL
        t_goRight = t_SRT_gR

    # TMS timing #
    if tms_time == None: tms_time = math.nan
    if tms_time == 'halfRT':
        tms_time = halfRT_R if right else halfRT_L                        # tms at half RT of responding hand

    # change values from ms to s representation #
    fixDur, maxRT, interDur, tms_time= np.array([fixDur, maxRT, interDur, tms_time])/1000

    # Stimuli #
    mainStim = goRight if right else goLeft                            # left or right goal and go stim
    goalStim = goalRight if right else goalLeft   
    if task in ("SRT_L", "SRT_R"):
        goalStim, mainStim = SRTgoalStim, SRTgoStim
    
    # Helping variables #
    responseTime, targetTime = math.nan, math.nan                         
    tms_sent, correct, fixed, cued, goed = [False]*5
    keyResp = []                                                          # all keys pressed during task

    ################## Running the trial ####################
    print(f'\n#### Start of trial_N: {trial_N}. Task: {task}. Catch: {is_catch}####', end ='')
    startTime = globalTimer.getTime()                                     # saving time of trial start
    while globalTimer.getTime()-startTime < fixDur + interDur + maxRT:    # the trial loop

        ########### Send trigger to TMS ##########
        if (not tms_sent) and (not math.isnan(tms_time)) and globalTimer.getTime()-startTime >= fixDur + interDur + tms_time:  #Timing of TMS-signal is relative to IS
            sendRemark(t_TMS) #Send tms marker via parallell to EEG
            sendTMS() # Send TMS trigger via serial
            tms_sent = (globalTimer.getTime()-startTime-fixDur-interDur)*1000
            print(f'# Sending signal to TMS at t(IS) + {tms_sent} ms', end ='')

        ########### Look for keypresses ##########
        keyResp = event.getKeys([keyLeft,keyRight, 'escape'], timeStamped = globalTimer)     # Look for new keypresses
        if len(keyResp) > 0:                                              # check if keys were pressed and grab them with timestamp
            responseTime = keyResp[-1][1]
            if keyResp[-1][0] == keyLeft:            # Send response trigger to EEG:
                sendRemark(t_respL)
            elif keyResp[-1][0] == keyRight:
                sendRemark(t_respR)
            else:
                sendRemark(t_respError)
            break                                                         # finish current trial and return to main script

        ############# Draw stimuli in order ##############
        if globalTimer.getTime()-startTime < fixDur and not fixed:        # Draw the fixation cross for fixDur ms
            fixation.draw()
            mywin.flip()
            sendRemark(t_fixStart) #Send fixation trigger to EEG:
            print(f' # Fixation started: {globalTimer.getTime()-startTime}', end ='')
            fixed = True
            
        if (fixDur < globalTimer.getTime()-startTime < fixDur+interDur) and not cued: #preparatory period
            if task == "UCRT":
                goalLeft.draw()
                goalRight.draw()
            else:
                goalStim.draw()                                               # Draw the preparatory cue
            mywin.flip()
            cued = True
            sendRemark(t_pCue)#Send eeg trigger for preparatory cue
            print(f' # PS shown: {globalTimer.getTime()-startTime}', end ='')

        elif (globalTimer.getTime()-startTime >= fixDur+interDur) and not goed: #imperative signal/catchX
                if is_catch: catchX.draw()
                else:
                    mainStim.draw()                                         # Draw the imperative signal (IS)
                    if task == "UCRT":
                        goalLeft.draw()
                        goalRight.draw()
                    else:
                        goalStim.draw()                                               # Draw the preparatory cue again
                mywin.flip()
                goed = True

                #Send eeg trigger for IS:
                if is_catch:
                    sendRemark(t_X)
                elif right:
                    sendRemark(t_goRight)
                else:
                    sendRemark(t_goLeft)
                
                if math.isnan(targetTime): targetTime = globalTimer.getTime()     # Save the time of IS
                print(f' # IS shown: {targetTime-startTime}', end ='')

        if event.getKeys(['escape']):
            datafile.close()
            mywin.close()
            core.quit()
        #print((time-globalTimer.getTime())*1000)                             # to test the speed of one while loop
    mywin.flip()
    if math.isnan(responseTime):
        sendRemark(t_timeout)  # send EEG info that trial ended by timeout 

    ############## Displaying feedback ################
    rt = (responseTime - targetTime)*1000                                     # representing rt in ms

    if (len(keyResp) > 0) and not is_catch:                                   # if not catch trial and response is given
        correct = correctKey == keyResp[-1][0]                                # is is correct if correct key was pressed.

    if (len(keyResp) > 0) and math.isnan(rt):                                   # Any response which is not a number is false
        correct = False

    if (len(keyResp)==0) and is_catch:                                        # No response is correct if trial is catch
        correct = True
 
    rt = math.nan if math.isnan(rt) else math.floor(rt)                       # RT is nan if no key press, else round down to nearest ms
    print(f' # RT: {rt}ms: at {responseTime-startTime},')
    infoStim.text = f'RT : {rt}ms'                                            # Show reaction time,
    infoStim.color = [0,128,0] if correct else [255,0,0]                      # in green if correct button press, else in red
    infoStim.draw()
    mywin.flip()
    core.wait(0.5)

    return trial_N, task, right, keyResp, rt, correct, tms_sent, is_catch, is_train

def createTrialList(randomSeed, RTTrials, catchRatio, trialsPerStimtimePerCondition, baselinesPerCondition, tasks = ['SRT_L', 'SRT_R', 'UCRT', 'ICRT']):
    """creates a list of tuples, eact tuple representing one set of conditions for each trial. 

    Args:
        ITI (_float_): intertrial interval represented in ms. 
        randomSeed (_int_): used for randomizing order of trials and tasks. 
        meanRTTrials (_int_): number of "training" trials per hand per task used to calculate meanRT. 
        catchRatio (_float_): between 0 and 1: a number of catch trials per non-catch trial,
         which is added to the total number of trials. (ratio is really the wrong word but). 
        trialsPerStimTimePerHand (_int_): the number of trials per stimulation time per hand. 

    Returns:
        _iterable_:  list of tuples, where one trial of the experiment is represented as one tuple
            each tuple has the structure (task, right, tms_time, is_catch, is_train)
    """
    random.seed(randomSeed)
    trialList = []                     # all the trials, inlcuding "training" and experiment trials. 

    ####### SRT_L trials #######
    SRT_L_train = [('SRT_L', False, None, False, True)]*int(RTTrials) + [('SRT_L', False, None, True, True)]*int(RTTrials*catchRatio)
    SRT_L_experiment = [('SRT_L', False, stimTime_BL, False, False)]*baselinesPerCondition  # add baseline trials
    for stimTime in stimTimes_SRT_L:
        SRT_L_experiment += [('SRT_L', False, stimTime, False, False)]*trialsPerStimtimePerCondition

    SRT_L_experiment = SRT_L_experiment + [('SRT_L', True, None, True, False)]*int(len(SRT_L_experiment)*catchRatio) # Add catch trials
    
    random.shuffle(SRT_L_train)
    random.shuffle(SRT_L_experiment)
    SRT_L_trials = SRT_L_train + SRT_L_experiment

    ####### SRT_R trials #######
    SRT_R_train = [('SRT_R',  True, None, False, True)]*int(RTTrials) + [('SRT_R',  True, None, True, True)]*int(RTTrials*catchRatio)
    SRT_R_experiment = [('SRT_R',  True, stimTime_BL, False, False)]*baselinesPerCondition  # Add baseline trials
    for stimTime in stimTimes_SRT_R:
        SRT_R_experiment += [('SRT_R',  True, stimTime, False, False)]*trialsPerStimtimePerCondition

    SRT_R_experiment = SRT_R_experiment + [('SRT_R', True, None, True, False)]*int(len(SRT_R_experiment)*catchRatio/2) \
         + [('SRT_R', False, None, True, False)]*int(len(SRT_R_experiment)*catchRatio/2) # Add L and R catch trials

    random.seed(randomSeed+1) #change seed between creating each of the task lists
    random.shuffle(SRT_R_train)
    random.shuffle(SRT_R_experiment)
    SRT_R_trials = SRT_R_train + SRT_R_experiment

    ####### UCRT trials #########
    UCRT_train = [('UCRT', True, None, False, True)]*int(RTTrials) \
        + [('UCRT', True, None, True, True)]*int(RTTrials*catchRatio/2)\
        + [('UCRT', False, None, False, True)]*int(RTTrials)\
        + [('UCRT', False, None, True, True)]*int(RTTrials*catchRatio/2)
    
    UCRT_experiment = [('UCRT', True, stimTime_BL, False, False)]*baselinesPerCondition \
        + [('UCRT', False, stimTime_BL, False, False)]*baselinesPerCondition
    for stimTime in stimTimes_UCRT:
        UCRT_experiment += [('UCRT', True, stimTime, False, False)]*trialsPerStimtimePerCondition \
            + [('UCRT', False, stimTime, False, False)]*trialsPerStimtimePerCondition \
    
    UCRT_experiment = UCRT_experiment + [('UCRT', True, None, True, False)]*int(len(UCRT_experiment)*catchRatio/2)\
         + [('UCRT', False, None, True, False)]*int(len(UCRT_experiment)*catchRatio/2) # Add L and R catch trials
    
    random.seed(randomSeed+2)
    random.shuffle(UCRT_train)
    random.shuffle(UCRT_experiment)
    UCRT_trials = UCRT_train + UCRT_experiment

        ####### ICRT trials #########
    ICRT_train = [('ICRT', True, None, False, True)]*int(RTTrials) \
        + [('ICRT', True, None, True, True)]*int(RTTrials*catchRatio/2)\
        + [('ICRT', False, None, False, True)]*int(RTTrials)\
        + [('ICRT', False, None, True, True)]*int(RTTrials*catchRatio/2)
    
    ICRT_experiment = [('ICRT', True, stimTime_BL, False, False)]*baselinesPerCondition \
        + [('ICRT', False, stimTime_BL, False, False)]*baselinesPerCondition
    for stimTime in stimTimes_ICRT:
        ICRT_experiment += [('ICRT', True, stimTime, False, False)]*trialsPerStimtimePerCondition \
            + [('ICRT', False, stimTime, False, False)]*trialsPerStimtimePerCondition \
    
    ICRT_experiment = ICRT_experiment + [('ICRT', True, None, True, False)]*int(len(ICRT_experiment)*catchRatio) # Add catch trials

    random.seed(randomSeed+3)
    random.shuffle(ICRT_train)
    random.shuffle(ICRT_experiment)
    ICRT_trials = ICRT_train + ICRT_experiment

    ##### Randomise the order of the various tasks #####
    sortList = [0,1,2,3]
    random.shuffle(sortList)
    for i in sortList:
        if i == 0 and 'SRT_L' in tasks:
            trialList += SRT_L_trials
        elif i == 1 and 'SRT_R' in tasks:
            trialList += SRT_R_trials
        elif i == 2 and 'UCRT' in tasks:
            trialList += UCRT_trials
        elif i == 3 and 'ICRT' in tasks:
            trialList += ICRT_trials

    return trialList

def runTrials(trialList, startFrom = 0, ITI = (4000, 4000), PCISI = (500, 500), maxRT = 1000):
    trialN = startFrom                                     # trialN is where we begin
    trialList = trialList[startFrom::]                     # Should not run everything again if instructed to start from anything other than 0
    last_is_train = False
    trainingRT_L = []                                      # to keep track of training RT, used for calculating half RT
    trainingRT_R = []                                      # to keep track of training RT, used for calculating half RT
    halfRT_L = 150                                         # should not be used before is redefined, but is defined as 150 by default
    halfRT_R = 150 

    lastTask = None
    lastBreak = globalTimer.getTime()
    for trial in trialList:
        if enableBreaks and (globalTimer.getTime() > lastBreak + breakInterval):
            sendRemark(t_pause)
            infoStim.text = "Now it is time for a short break \n Press the middle key when you are ready to continue"
            infoStim.color = [1,1,1]; infoStim.draw(); mywin.flip()
            print("\n # User is breaking - taking a break")
            event.waitKeys(keyList = ['d'])            # Wait for user to press the middle key

        randFix = np.random.uniform(ITI[0], ITI[1])      # random fixation time between ITImin and ITImax
        randInt = np.random.uniform(PCISI[0], PCISI[1])    # random interval between PC and IS in ICRT
        task = trial[0]
        right = trial[1]
        tms_time = trial[2]
        is_catch = trial[3]
        is_train = trial[4]

        if task != lastTask:
            infoStim.text = "Now it is time for a new task. \n\nPress the middle key to read the instructions"
            infoStim.color = [1,1,1]; infoStim.draw(); mywin.flip()
            start = event.waitKeys(keyList = ['d'])            # Wait for user to press the middle key to continue

            ######## Show instructions ########
            if task == 'SRT_R':
                infoStim.text = "Time for a simple reaction time task.\n\nRespond with *right index finger* on the *yellow* key when you see the white ball. \n\nPress the middle key to begin"
                print("# SRT_R instructions")
            elif task == 'SRT_L':
                infoStim.text = "Time for a simple reaction time task.\n\nRespond with *left index finger* on the *red* key when you see the ball and goal. \n\nPress the middle key to begin"
                print("# SRT_L instructions")
            elif task == 'UCRT':
                infoStim.text = "Time for a choice reaction time task.\n\nRespond with *right index finger* on the *yellow* key or *left index finger* on the *red* key according to direction of ball and goal. \n\nPress the middle key to begin"
                print("# UCRT instructions")
            elif task == 'ICRT':
                infoStim.text = "Time for an informed choice reaction time task.\n\nRespond with *right index finger* on the *yellow* key or *left index finger* on the *red* key according to direction of ball and goal. \n\nDo not press before you see the ball. \n\nPress the middle key to begin"
                print("# ICRT instructions")
            infoStim.color = [1,1,1]; infoStim.draw(); mywin.flip()
            start = event.waitKeys(keyList = ['d'])              # Wait for user to press the middle key to begin block
            lastBreak = globalTimer.getTime()
            sendRemark(t_startBlock)  # start of block EEG marker

        if last_is_train and (not is_train):                         # if last trial as training and current is not, meanRT shuld be calculated from previous trials
            if len(trainingRT_L)>0:
                halfRT_L = np.nanmean(trainingRT_L)/3
                print(f' halfRT_L was calculated based on previous trials')
            if len(trainingRT_R)>0:
                halfRT_R = np.nanmean(trainingRT_R)/3
                print(f' halfRT_R was calculated based on previous trials')
            trainingRT_L = []                                      # reset for next task
            trainingRT_R = []                                      # reset for next task
        
        ###### Run and write the trial to file#######
        temp = trialRT1(trialN, task, tms_time, fixDur = randFix, maxRT = maxRT, interDur = randInt, right = right, is_catch = is_catch, halfRT_R=halfRT_R, halfRT_L=halfRT_L, is_train=is_train)
        temp = list(temp)
        temp.append(globalTimer.getTime())
        writer.writerow(temp)
        
        #temp: trial_N, task, right, keyResp, rt, correct, tms_sent, is_catch
        if is_train:
            if temp[5]: #if response was correct
                if right:
                    trainingRT_R.append(temp[4]) # add rt to right RT list
                    print(f' Added R RT to list')
                else:
                    trainingRT_L.append(temp[4]) # add rt to left RT list
                    print(f' Added L RT to list')
            else:
                print(f' Response was incorrect, could not add RT to list')

        lastTask = task
        last_is_train = is_train
        trialN += 1

# %% A function to run pure TMS baseline measures. 
def baselineMeasures(numberoftrials):
    infoStim.text = "Time for some baseline measures. Please relax. \n Press the middle key to begin"
    infoStim.draw()
    mywin.flip()
    event.waitKeys(keyList = ['d'])            # Wait for user to press the middle key to press continue
    fixation.draw()
    mywin.flip()
    for i in range(numberoftrials):
        core.wait(random.randint(5,8))
        sendRemark(t_TMS) #Send tms marker via parallell to EEG
        sendTMS()#Send trigger to TMS via serial
        print('# BL measure: sending signal to TMS')
        temp = [f'BL: {i}', "BL", None, None, None, None, True, None, False, globalTimer.getTime()]
        writer.writerow(temp) #write data to file
        if event.getKeys(['escape']):
            datafile.close()
            mywin.close()
            core.quit()
    return

# %% Run the show
mywin.mouseVisible = False
## Create the list of trials. This used subject ID as seed for randomization, so re-running the script for same participant whould return the same experiment. 
trialList = createTrialList(info['Subject ID'], RTtrials, catchRatio, trialsPerStimtimePerCondition, baselinesPerCondition, tasks)
## Run the trials created
sendRemark(t_startExp) # send start trigger to EEG 
baselineMeasures(bl_before) #Baseline measures before
runTrials(trialList, info['Start from trial:'], ITI = ITI, PCISI = PCISI, maxRT = maxRT) #Main experiment.
baselineMeasures(bl_after) #Baselines measure after
infoStim.text = "Experiment finished. \n Thank you for participating. \n \n Press the middle key to quit"
infoStim.draw()
mywin.flip()
sendRemark(t_endExp) # EEG marker end of experiment
event.waitKeys(keyList = ['d'])            # Wait for user to press the middle key to press continue

# %% Save, close and quit. 
datafile.close()
mywin.close()
core.quit()