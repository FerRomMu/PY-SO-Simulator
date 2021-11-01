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

    kernel = Kernel(FCFSScheduler)

    mm = MemoryManager(5)
    usados = mm.allocFrames(2)
    mm.freeFrames(usados)

    # Ahora vamos a intentar ejecutar 3 programas a la vez
    ##################
    prg1 = Program("prg1.exe", [ASM.CPU(2), ASM.IO(), ASM.CPU(3), ASM.IO(), ASM.CPU(2)])
    prg2 = Program("prg2.exe", [ASM.CPU(7)])
    prg3 = Program("prg3.exe", [ASM.CPU(4), ASM.IO(), ASM.CPU(1)])

    kernel.fileSystem.write("c:/prog1.exe", prg1)
    kernel.fileSystem.write("c:/prog2.exe", prg2)
    kernel.fileSystem.write("c:/prog3.exe", prg3)


    # execute all programs "concurrently"
    # kernel.run("c:/prog1.exe", 0)
    # kernel.run("c:/prog2.exe", 1)
    # kernel.run("c:/prog3.exe", 2)







