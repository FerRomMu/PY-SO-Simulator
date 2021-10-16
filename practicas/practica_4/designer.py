import log


##un objeto que haga "marcos" y otras utilidades con el logger a fines esteticos
class LoggerDesign():

    def __init__(self):
        self._proceso = ["|Proceso|"]
        self._queue = ["|ReadyQ |"]

    def printGantt(self, table):
        self.actualizarProcesos(table)
        self.actualizarQueue(table)
        for text in self._proceso:
            log.logger.info(text)
        for text in self._queue:
            log.logger.info(text)

    #imprime una barra de largo 80
    def printBar(self):
        log.logger.info("|==============================================================================|")

    #imprime titulo de 3 renglones, con texto centrado
    def title(self, title):
        self.printBar()
        self.centerMessage(title)
        self.printBar()
        print()

    #imprime texto centrado
    def centerMessage(self, message):
        log.logger.info("|" + message.center(78) + "|")

    def actualizarProcesos(self, table):
        pass

    def actualizarQueue(self, table):
        pass


DESIGNER = LoggerDesign()