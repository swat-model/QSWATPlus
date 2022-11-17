import PyQt5

#
PyQt5.uic.compileUiDir("K:/Users/Public/QSWATPlus3/QSWATPlus", from_imports=True)  # @UndefinedVariable
# need relative import of resources_rc for next 2
convFile = open("K:/Users/Public/QSWATPlus3/QSWATPlus/ui_convert.py", 'w')
PyQt5.uic.compileUi("K:/Users/Public/QSWATPlus3/QSWATPlus/ui_convert.ui", convFile)  # @UndefinedVariable
convFile.close()
graphFile = open("K:/Users/Public/QSWATPlus3/QSWATPlus/ui_graph1.py", 'w')
PyQt5.uic.compileUi("K:/Users/Public/QSWATPlus3/QSWATPlus/ui_graph.ui", graphFile)  # @UndefinedVariable
graphFile.close()

