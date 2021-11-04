import PyQt5

#
PyQt5.uic.compileUiDir("G:/Users/Public/QSWATPlus3/QSWATPlus", from_imports=True)  # @UndefinedVariable
# need relative import of resources_rc for next 2
convFile = open("G:/Users/Public/QSWATPlus3/QSWATPlus/ui_convert.py", 'w')
PyQt5.uic.compileUi("G:/Users/Public/QSWATPlus3/QSWATPlus/ui_convert.ui", convFile)  # @UndefinedVariable
convFile.close()
graphFile = open("G:/Users/Public/QSWATPlus3/QSWATPlus/ui_graph1.py", 'w')
PyQt5.uic.compileUi("G:/Users/Public/QSWATPlus3/QSWATPlus/ui_graph.ui", graphFile)  # @UndefinedVariable
graphFile.close()

