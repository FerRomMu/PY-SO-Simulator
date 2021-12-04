from hardware import *
from so import *
from designer import *
import log

##
##  MAIN 
##
if __name__ == '__main__':
    log.setupLogger()
    DESIGNER.title('Starting emulator')

    ## setup our hardware and set memory size to 25 "cells"
    HARDWARE.setup(32)

    ## Switch on computer
    HARDWARE.switchOn()
    HARDWARE._cpu.enable_stats = True

    ## new create the Operative System Kernel
    # "booteamos" el sistema operativo
    
    #Settear tamaño de frames
    frames = 4

    #Elegir scheduler: 
    #   FCFSScheduler()
    #   PriorityScheduler(False, 0) --Poner True y un número para activar aging, puede inicializar sin parametros
    #   PreemtivePriorityScheduler(False, 0)
    #   RoundRobin(3) --Poner un valor de quantum para inicializar o dejarlo en 3.
    scheduler = PriorityScheduler(True, 3)
    kernel = Kernel(scheduler, frames)

    # Ahora vamos a intentar ejecutar 3 programas a la vez
    ##################
    '''
    prg1 = Program("prg1.exe", [ASM.CPU(2), ASM.IO(), ASM.CPU(3), ASM.IO(), ASM.CPU(2)])
    prg2 = Program("prg2.exe", [ASM.CPU(7)])
    prg3 = Program("prg3.exe", [ASM.CPU(4), ASM.IO(), ASM.CPU(1)])
    '''
    #Ejercicio A gantt
    prg1= Program("prg1.exe", [ASM.CPU(4)]) #[cpu x 5, 3]
    prg2= Program("prg2.exe", [ASM.CPU(2)]) #[cpu x 3, 5] <- tiempo llegada 2
    prg3= Program("prg3.exe", [ASM.CPU(5)]) #[cpu x 6, 2] <- 1
    prg4= Program("prg4.exe", [ASM.CPU(3)]) #[cpu x 4, 1] <- 1
    '''
    kernel.fileSystem.write("c:/prog1.exe", prg1)
    kernel.fileSystem.write("c:/prog2.exe", prg2)
    kernel.fileSystem.write("c:/prog3.exe", prg3)
    '''
    kernel.fileSystem.write("c:/prog1.exe", prg1)
    kernel.fileSystem.write("c:/prog2.exe", prg2)
    kernel.fileSystem.write("c:/prog3.exe", prg3)
    kernel.fileSystem.write("c:/prog4.exe", prg4)

    # execute all programs "concurrently"
    kernel.run("c:/prog1.exe", 1)
    kernel.runWithDelay("c:/prog3.exe", 2, 1)
    kernel.run("c:/prog4.exe", 1)
    kernel.runWithDelay("c:/prog2.exe", 5, 1)







