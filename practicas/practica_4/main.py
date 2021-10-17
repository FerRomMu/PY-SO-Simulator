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
    DESIGNER.printBar()
    # setup our hardware and set memory size to 25 "cells"
    HARDWARE.setup(25)

    ## Switch on computer
    HARDWARE.switchOn()
    HARDWARE.cpu.enable_stats = True    # habilita flag enable_stats

    ## new create the Operative System Kernel
    # "booteamos" el sistema operativo
    schedule = RoundRobin(3)
    kernel = Kernel(schedule)

    # Ahora vamos a intentar ejecutar 3 programas a la vez
    ##################
    prg1 = Program("prg1.exe", [ASM.CPU(2), ASM.IO(), ASM.CPU(3), ASM.IO(), ASM.CPU(2)])
    prg2 = Program("prg2.exe", [ASM.CPU(7)])
    prg3 = Program("prg3.exe", [ASM.CPU(4), ASM.IO(), ASM.CPU(1)])

    # execute all programs "concurrently"
    kernel.run(prg1, 3)
    kernel.run(prg2, 6)
    kernel.run(prg3, 1)




