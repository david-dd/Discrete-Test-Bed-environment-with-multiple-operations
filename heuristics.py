from tkinter import S
#import gym
import numpy as np
from random import *               

import os
import numpy as np
import matplotlib.pyplot as plt
import math

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import torch.autograd as autograd
from torch.autograd import Variable

from torch.distributions import Categorical

###########################################################
###########################################################
### Import custom Libraries
###########################################################
###########################################################

import pickle

from _env import *

def start(algoName, modus): 

    ###########################################################
    ###########################################################
    ### Settings
    ###########################################################
    ###########################################################

    ###########################################################
    ### Init
    ###########################################################
    # Change cyclically from 0 to 1 to 2 to 3 and again to 0
    OpRoundRobin=[
        0,      # Op10
        0,      # Op20
        0,      # Op30
        0,      # Op40
        0,      # Op50
        0,      # Op60
        0       # Op70
         ]
   
    ###########################################################
    ### Eval Setting
    ###########################################################
    
    # Loading the evaluation dataset
    cur_path = os.path.dirname(__file__)
    new_path = os.path.relpath('evalDatasets.pkl', cur_path)
    
    with open(new_path, 'rb') as f: 
        evalDatasets = pickle.load(f)


    ammountOfDatasetsEval   = len(evalDatasets[0])
    
    evalMakespan            = []
    evalOverallWaiting      = []
    evalOverallparalelTimes = []

    for k,records in enumerate(evalDatasets):

        
        ammountOfCarriers   = records[0][0][0]                     
        ammountOfProducts   = records[0][0][1]                      
        uncertainty         = records[0][0][2]           
        breakdowns          = records[0][0][3]     

        evalMakespan.append([])
        evalOverallWaiting.append([])
        evalOverallparalelTimes.append([])

        ###########################################################
        ### Setup Env and Agent
        ###########################################################

        env = marlEnvironment(uncertainty,ammountOfCarriers, False, ammountOfProducts, breakdowns)

        
        ###########################################################
        ###########################################################
        ### Start Eval
        ###########################################################
        ###########################################################
        epiCounter = 0
 

        for d in records:
            #  0        , 1       , 2        
            # `conveyor`,`carrier`,`stations`
            settings    = d[0]
            conveyor    = d[1]
            carrier     = d[2]
            stations    = d[3]
            order       = d[4]


            done, duration, state, [popedStationKey, popedWorkplanKey,popedCarrierKey, popedOp, orderKey, tempReward] = env.startAnEvalEpisode(conveyor,carrier,stations, order)
        

            j = 0
            actions = []
            while not done:

                #Entscheidung    0,2    1,3
                #Entscheidung    00,10  01,11
                #OpA		    [0       ]          # Op1
                #OpB 		    [1,     2]          # Op2
                #OpC		    [2,     3]          # Op3
                #OpD		    [0,     1]          # Op4
                #OpE		    [0,     1]          # Op5
                #OpF		    [2,     3]          # Op6
                #OpG		    [3       ]          # op7

                action = 0
                # Action ist abhänig vom Modus
                # 0 = "Shortest Processing Time First"
                # 1 = "Longest Processing Time First"
                # 2 = "Shortest Path First"
                # 3 = "RoundRobin"
                # 4 = "Random"

                if modus == 0:
                    # 0 = "Shortest Processing Time First"
                    if popedOp == 2:
                        # OpB = Op2 
                        # 15 seconds at Station=2 (key=1)
                        # 15 seconds at Station=3 (key=2)
                        # Also immer Station=2 (key=1)
                        action = 0
                    if popedOp == 3:
                        # OpC = Op3 
                        # 19 seconds at Station=3 (key=2)
                        # 16 seconds at Station=4 (key=3)
                        # Also immer Station=4 (key=3)
                        action = 1
                    if popedOp == 4:
                        # OpD = Op4 
                        # 22 seconds at Station=1 (key=0)
                        # 18 seconds at Station=2 (key=1)
                        # Also immer Station=2 (key=1)
                        action = 1
                    if popedOp == 5:
                        # OpE = Op5 
                        # 19 seconds at Station=1 (key=0)
                        # 24 seconds at Station=2 (key=1)
                        # Also immer Station=1 (key=0)
                        action = 0
                    if popedOp == 6:
                        # OpF = Op6 
                        # 19 seconds at Station=3 (key=2)
                        # 17 seconds at Station=4 (key=3)
                        # Also immer Station=4 (key=3)
                        action = 1
                elif modus == 1:
                    # 1 = "Longest Processing Time First"
                    if popedOp == 2:
                        # OpB = Op2 
                        # 15 seconds at Station=2 (key=1)
                        # 15 seconds at Station=3 (key=2)
                        # Also immer Station=3 (key=2)
                        action = 1
                    if popedOp == 3:
                        # OpC = Op3 
                        # 19 seconds at Station=3 (key=2)
                        # 16 seconds at Station=4 (key=3)
                        # Also immer Station=3 (key=2)
                        action = 0
                    if popedOp == 4:
                        # OpD = Op4 
                        # 22 seconds at Station=1 (key=0)
                        # 18 seconds at Station=2 (key=1)
                        # Also immer Station=1 (key=0)
                        action = 0
                    if popedOp == 5:
                        # OpE = Op5 
                        # 19 seconds at Station=1 (key=0)
                        # 24 seconds at Station=2 (key=1)
                        # Also immer Station=2 (key=1)
                        action = 1
                    if popedOp == 6:
                        # OpF = Op6 
                        # 19 seconds at Station=3 (key=2)
                        # 17 seconds at Station=4 (key=3)
                        # Also immer Station=3 (key=2)
                        action = 0
                elif modus == 2:
                    # 2 = "Shortest Path First"
                        if popedStationKey == 0:
                            # Station 1
                            if popedOp == 2:    # OpB = Op2                            
                                action = 0      # Options: S=2 or S=3 -> Shortest way is S=2 (key=1)  
                            elif popedOp == 3:  # OpC = Op3                              
                                action = 0      # Options: S=3 or S=4 -> Shortest way is S=3 (key=2)
                            elif popedOp == 4:  # OpD = Op4                               
                                action = 0      # Options: S=1 or S=2 -> Shortest way is S=1 (key=0)  
                            elif popedOp == 5:  # OpE = Op5                               
                                action = 0      # Options: S=1 or S=2 -> Shortest way is S=1 (key=0)
                            elif popedOp == 6:  # OpF = Op6                               
                                action = 0      # Options: S=3 or S=4 -> Shortest way is S=3 (key=2)
                        elif popedStationKey == 2:
                            # Station 2
                            if popedOp == 2:    # OpB = Op2                            
                                action = 0      # Options: S=2 or S=3 -> Shortest way is S=2 (key=1)  
                            elif popedOp == 3:  # OpC = Op3                              
                                action = 0      # Options: S=3 or S=4 -> Shortest way is S=3 (key=2)
                            elif popedOp == 4:  # OpD = Op4                               
                                action = 1      # Options: S=1 or S=2 -> Shortest way is S=2 (key=1)  
                            elif popedOp == 5:  # OpE = Op5                               
                                action = 1      # Options: S=1 or S=2 -> Shortest way is S=2 (key=1)
                            elif popedOp == 6:  # OpF = Op6                               
                                action = 0      # Options: S=3 or S=4 -> Shortest way is S=3 (key=2)
                        elif popedStationKey == 3:
                            # Station 3
                            if popedOp == 2:    # OpB = Op2                            
                                action = 1      # Options: S=2 or S=3 -> Shortest way is S=3 (key=2)  
                            elif popedOp == 3:  # OpC = Op3                              
                                action = 0      # Options: S=3 or S=4 -> Shortest way is S=3 (key=2)
                            elif popedOp == 4:  # OpD = Op4                               
                                action = 0      # Options: S=1 or S=2 -> Shortest way is S=1 (key=0)  
                            elif popedOp == 5:  # OpE = Op5                               
                                action = 0      # Options: S=1 or S=2 -> Shortest way is S=1 (key=0)
                            elif popedOp == 6:  # OpF = Op6                               
                                action = 0      # Options: S=3 or S=4 -> Shortest way is S=3 (key=2)
                        elif popedStationKey == 4:
                            # Station 5
                            if popedOp == 2:    # OpB = Op2                            
                                action = 0      # Options: S=2 or S=3 -> Shortest way is S=2 (key=1)  
                            elif popedOp == 3:  # OpC = Op3                              
                                action = 1      # Options: S=3 or S=4 -> Shortest way is S=4 (key=3)
                            elif popedOp == 4:  # OpD = Op4                               
                                action = 0      # Options: S=1 or S=2 -> Shortest way is S=1 (key=0)  
                            elif popedOp == 5:  # OpE = Op5                               
                                action = 0      # Options: S=1 or S=2 -> Shortest way is S=1 (key=0)
                            elif popedOp == 6:  # OpF = Op6                               
                                action = 1      # Options: S=3 or S=4 -> Shortest way is S=4 (key=3)
                elif modus == 3:
                    # 3 = "RoundRobin" 
                    action = OpRoundRobin[popedOp]      # Load last decision
                    action += 1                         # Jump to next alternative
                    if action > 3:                      # Check if border is reached
                        action = 0                      # If yes, then go back to start
                    OpRoundRobin[popedOp] = action      # Deposit new action in the array
                elif modus == 4:
                    # 4 ="Random"
                    action = random.choice([0,1,2,3])   


                actions.append(action)                    
        
                done, duration, nextState, [popedStationKey, popedWorkplanKey,popedCarrierKey, popedOp, orderKey, tempReward] = env.step(action)   
                state = nextState

                j = j +1


            reward, overallWaiting, overallparalelTimes = env.calcReward(duration)
            evalMakespan[k].append(duration)
            evalOverallWaiting[k].append(overallWaiting)
            evalOverallparalelTimes[k].append(overallparalelTimes)

            print("Name=", algoName, "Evalset", k,  "Episode=" , epiCounter, "Duration=", duration, "Order length=", len(order)) 
            epiCounter +=1
        


    ###########################################################    
    # Output evaluation results
    ###########################################################

    print("###########################################################")
    print("###########################################################")
    for k,records in enumerate(evalDatasets):
        avg_eval_makespan = np.mean(evalMakespan[k][-ammountOfDatasetsEval:])
        avg_eval_waiting = np.mean(evalOverallWaiting[k][-ammountOfDatasetsEval:])
        avg_eval_paralel = np.mean(evalOverallparalelTimes[k][-ammountOfDatasetsEval:])

        print("Evaluierung des Modells mit dem Evalset#"+str(k),)
        print("Makespan", "min" , min(evalMakespan[k])          ,"avg:" , avg_eval_makespan  , "max" , max(evalMakespan[k])) 
        print("Waiting:", "min", min(evalOverallWaiting[k])     ,"avg"  , avg_eval_waiting   , "max" , max(evalOverallWaiting[k]))
        print("Paralel:", "min", min(evalOverallparalelTimes[k]),"avg"  , avg_eval_paralel   , "max" , max(evalOverallparalelTimes[k]))
        print()    
    print("###########################################################")


###########################################################
###########################################################
### Start Process
###########################################################
###########################################################

if __name__ == '__main__':


    ###########################################################
    ###########################################################
    ### Heuristics
    ###########################################################
    ###########################################################   
    
    modus = []
    modus.append(["Shortest Processing Time First" , 0])
    modus.append(["Longest Processing Time First" , 1])
    modus.append(["Shortest Path First" , 2])
    modus.append(["RoundRobin" , 3])
    modus.append(["Random" , 4])

    for m in modus:
        
        

        algoName = m[0]
        i = m[1]
        print("###########################################################")
        print("Auswertung der statischen Lösung startet:")
        print()
        print("algoName=", algoName)
        print()
        res = start(algoName, i)
        print("###########################################################")

                