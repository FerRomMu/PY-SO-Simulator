from hardware import *
from so import *
import log


##
##  MAIN 
##
if __name__ == '__main__':
    log.setupLogger()
    log.logger.info('Starting emulator')

    ## setup our hardware and set memory size to 25 "cells"
    HARDWARE.setup(30)

    ## Switch on computer
    HARDWARE.switchOn()

    ## new create the Operative System Kernel
    # "booteamos" el sistema operativo
    
    #Settear tamaño de frames
    frames = 5

    #Elegir scheduler: 
    #   FCFSScheduler()
    #   PriorityScheduler(False, 0) --Poner True y un número para activar aging, puede inicializar sin parametros
    #   PreemtivePriorityScheduler(False, 0)
    #   RoundRobin(3) --Poner un valor de quantum para inicializar o dejarlo en 3.
    scheduler = FCFSScheduler()
    kernel = Kernel(scheduler, frames)

    '''mm = MemoryManager(5)
    usados = mm.allocFrames(2)
    mm.freeFrames(usados)'''

    # Ahora vamos a intentar ejecutar 3 programas a la vez
    ##################
    prg1 = Program("prg1.exe", [ASM.CPU(2), ASM.IO(), ASM.CPU(3), ASM.IO(), ASM.CPU(2)])
    prg2 = Program("prg2.exe", [ASM.CPU(7)])
    prg3 = Program("prg3.exe", [ASM.CPU(4), ASM.IO(), ASM.CPU(1)])

    kernel.fileSystem.write("c:/prog1.exe", prg1)
    kernel.fileSystem.write("c:/prog2.exe", prg2)
    kernel.fileSystem.write("c:/prog3.exe", prg3)

    kernel.fileSystem.read("c:/prog1.exe")
    kernel.fileSystem.read("c:/prog2.exe")
    kernel.fileSystem.read("c:/prog3.exe")


    # execute all programs "concurrently"
    kernel.run("c:/prog1.exe", 0)
    # kernel.run("c:/prog2.exe", 1)
    # kernel.run("c:/prog3.exe", 2)







