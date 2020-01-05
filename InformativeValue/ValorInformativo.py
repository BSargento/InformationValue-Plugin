# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ValorInformativo
                                 A QGIS plugin
 Calcula o Valor Informativo
                              -------------------
        begin                : 2017-12-21
        git sha              : $Format:%H$
        copyright            : (C) 2017 by BSargento
        email                : bernardosargento@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QTableWidgetItem, QProgressBar
from qgis.core import *
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from ValorInformativo_dialog import ValorInformativoDialog

import os, sys, processing, math, numpy, csv, re
from qgis.PyQt.QtCore import *
from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry
from qgis.gui import QgsMessageBar
from operator import itemgetter

class ValorInformativo:
	"""QGIS Plugin Implementation."""

	def __init__(self, iface):
		"""Constructor.

		:param iface: An interface instance that will be passed to this class
			which provides the hook by which you can manipulate the QGIS
			application at run time.
		:type iface: QgsInterface
		"""
		# Save reference to the QGIS interface
		self.iface = iface
		# initialize plugin directory
		self.plugin_dir = os.path.dirname(__file__)
		# initialize locale
		locale = QSettings().value('locale/userLocale')[0:2]
		locale_path = os.path.join(
			self.plugin_dir,
			'i18n',
			'ValorInformativo_{}.qm'.format(locale))

		if os.path.exists(locale_path):
			self.translator = QTranslator()
			self.translator.load(locale_path)

			if qVersion() > '4.3.3':
				QCoreApplication.installTranslator(self.translator)

		# Create the dialog (after translation) and keep reference
		self.dlg = ValorInformativoDialog()

		# Declare instance attributes
		self.actions = []
		self.menu = self.tr(u'&Valor Informativo')
		# TODO: We are going to let the user set this up in a future iteration
		self.toolbar = self.iface.addToolBar(u'ValorInformativo')
		self.toolbar.setObjectName(u'ValorInformativo')
		
		self.dlg.lineEdit_2.clear()
		self.dlg.lineEdit_3.clear()
		self.dlg.lineEdit_4.clear()
		self.dlg.lineEdit_5.clear()		
		self.dlg.toolButton_2.clicked.connect(lambda: self.VariavelDependente(self.dlg.lineEdit_2, self.dlg.lineEdit_4))
		self.dlg.toolButton_3.clicked.connect(self.SelecionarOutputPath)
		self.dlg.toolButton_4.clicked.connect(self.SelecionarVariaveisIndependentes)
		self.dlg.toolButton_5.clicked.connect(self.RemoverVariavelIndependente)
		self.dlg.toolButton_6.clicked.connect(lambda: self.RasterValidacao(self.dlg.lineEdit_5, self.dlg.lineEdit_6))

	# noinspection PyMethodMayBeStatic
	def tr(self, message):
		"""Get the translation for a string using Qt translation API.

		We implement this ourselves since we do not inherit QObject.

		:param message: String for translation.
		:type message: str, QString

		:returns: Translated version of message.
		:rtype: QString
		"""
		# noinspection PyTypeChecker,PyArgumentList,PyCallByClass
		return QCoreApplication.translate('ValorInformativo', message)


	def add_action(
		self,
		icon_path,
		text,
		callback,
		enabled_flag=True,
		add_to_menu=True,
		add_to_toolbar=True,
		status_tip=None,
		whats_this=None,
		parent=None):
		"""Add a toolbar icon to the toolbar.

		:param icon_path: Path to the icon for this action. Can be a resource
			path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
		:type icon_path: str

		:param text: Text that should be shown in menu items for this action.
		:type text: str

		:param callback: Function to be called when the action is triggered.
		:type callback: function

		:param enabled_flag: A flag indicating if the action should be enabled
			by default. Defaults to True.
		:type enabled_flag: bool

		:param add_to_menu: Flag indicating whether the action should also
			be added to the menu. Defaults to True.
		:type add_to_menu: bool

		:param add_to_toolbar: Flag indicating whether the action should also
			be added to the toolbar. Defaults to True.
		:type add_to_toolbar: bool

		:param status_tip: Optional text to show in a popup when mouse pointer
			hovers over the action.
		:type status_tip: str

		:param parent: Parent widget for the new action. Defaults None.
		:type parent: QWidget

		:param whats_this: Optional text to show in the status bar when the
			mouse pointer hovers over the action.

		:returns: The action that was created. Note that the action is also
			added to self.actions list.
		:rtype: QAction
		"""

		icon = QIcon(icon_path)
		action = QAction(icon, text, parent)
		action.triggered.connect(callback)
		action.setEnabled(enabled_flag)

		if status_tip is not None:
			action.setStatusTip(status_tip)

		if whats_this is not None:
			action.setWhatsThis(whats_this)

		if add_to_toolbar:
			self.toolbar.addAction(action)

		if add_to_menu:
			self.iface.addPluginToVectorMenu(
			self.menu,
			action)

		self.actions.append(action)

		return action

	def initGui(self):
		"""Create the menu entries and toolbar icons inside the QGIS GUI."""

		icon_path = ':/plugins/ValorInformativo/icon.png'
		self.add_action(
		icon_path,
		text=self.tr(u'Calcula o Valor Informativo'),
		callback=self.run,
		parent=self.iface.mainWindow())
		
	def unload(self):
		"""Removes the plugin menu item and icon from QGIS GUI."""
		for action in self.actions:
			self.iface.removePluginVectorMenu(
				self.tr(u'&Valor Informativo'),
				action)
			self.iface.removeToolBarIcon(action)
		# remove the toolbar
		del self.toolbar


# PARAMETRO 1 - "VARIAVEIS INDEPENDENTES"
	def SelecionarVariaveisIndependentes(self):
		VarIndepInputLista = QFileDialog.getOpenFileNames(self.dlg, "Selecionar um ou mais rasters", "/Users/bsargento/Desktop/TesteVC/DADOS_BASE/", "TIFF / BigTIFF / GeoTIFF (*.tif);;Arc/Info Binary Grid (*.adf)")
		if VarIndepInputLista is not None:
			for VarIndepInput in VarIndepInputLista:
				VarIndepLayerName = os.path.basename(VarIndepInput).rsplit(".")[0]
				InFileObject = processing.getObject(VarIndepInput)
				if InFileObject.type() == QgsMapLayer.RasterLayer:
					rowPosition = self.dlg.tableWidget.rowCount()
					self.dlg.tableWidget.insertRow(rowPosition)
					NrColunas = self.dlg.tableWidget.columnCount()
					NrLinhas = self.dlg.tableWidget.rowCount()           
					self.dlg.tableWidget.setRowCount(NrLinhas)
					self.dlg.tableWidget.setColumnCount(NrColunas)           
					self.dlg.tableWidget.setItem(NrLinhas -1,0,QTableWidgetItem(VarIndepInput))
					self.dlg.tableWidget.setItem(NrLinhas -1,1,QTableWidgetItem(VarIndepLayerName))		

					
	def RemoverVariavelIndependente(self):
		self.dlg.tableWidget.currentRow()
		self.dlg.tableWidget.removeRow(self.dlg.tableWidget.currentRow())
	
# PARAMETRO 2 - "VARIAVEL DEPENDENTE"
	def VariavelDependente(self, lineEdit_2, lineEdit_4):
		VarDepInput = str(QFileDialog.getOpenFileNames(self.dlg, "Selecionar um ficehiro raster", "/Users/bsargento/Desktop/TesteVC/DADOS_BASE/", "TIFF / BigTIFF / GeoTIFF (*.tif);;Arc/Info Binary Grid (*.adf)")[0])
		if VarDepInput is not None:
			VarDepLayerName = os.path.basename(VarDepInput).rsplit(".")[0]
			InFileObject = processing.getObject(VarDepInput)
			if InFileObject.type() == QgsMapLayer.RasterLayer:
				lineEdit_2.setText(VarDepInput)
				lineEdit_4.setText(VarDepLayerName)

# PARAMETRO 3 - "OUTPUT FOLDER"		
	def SelecionarOutputPath(self):
		OutputPath = QFileDialog.getExistingDirectory(self.dlg, "Guardar em","/Users/bsargento/Desktop/")
		self.dlg.lineEdit_3.setText(OutputPath)

# PARAMETRO 4 - "VARIAVEL DE VALIDACAO"
	def RasterValidacao(self, lineEdit_5, lineEdit_6):
		RasterValidacaoInput = str(QFileDialog.getOpenFileNames(self.dlg, "Selecionar um ficehiro raster", "/Users/bsargento/Desktop/TesteVC/DADOS_BASE/", "TIFF / BigTIFF / GeoTIFF (*.tif);;Arc/Info Binary Grid (*.adf)")[0])
		if RasterValidacaoInput is not None:
			VarValidacaoLayerName = os.path.basename(RasterValidacaoInput).rsplit(".")[0]
			InFileObject = processing.getObject(RasterValidacaoInput)
			if InFileObject.type() == QgsMapLayer.RasterLayer:
				lineEdit_5.setText(RasterValidacaoInput)
				lineEdit_6.setText(VarValidacaoLayerName)		
		

# EXECUCAO DO MODELO:		
	def run(self):
		"""Run method that performs all the real work"""
		
		# show the dialog
		self.dlg.show()
		# Run the dialog event loop
		result = self.dlg.exec_()
		# See if OK was pressed
		if result:
		
	# CARREGAR VALORES DOS PARAMETROS:
		#PARAMETRO 1
			ListaVarIndep = []
			ListaLayerName = []
			NrLinhasTabela = self.dlg.tableWidget.rowCount()
			for Linhas in range(NrLinhasTabela):
				VarIndepPath = self.dlg.tableWidget.item(Linhas, 0).text()
				VarIndepLayerName = self.dlg.tableWidget.item(Linhas, 1).text()
				ListaVarIndep.append(VarIndepPath)
				ListaLayerName.append(VarIndepLayerName)
				
		#PARAMETRO 2
			VarDep = self.dlg.lineEdit_2.text()
			VarDepDisplayName = self.dlg.lineEdit_4.text()
			
		#PARAMETRO 3
			InputOutputFolder = self.dlg.lineEdit_3.text()

		#PARAMETRO 4
			RasterValidacao = self.dlg.lineEdit_5.text()
			ValidacaoDisplayName = self.dlg.lineEdit_6.text()

	# INICIO DOS PROCESSOS:		
		# CRIAR PASTA OUTPUT
			PastaOutput = os.path.join(InputOutputFolder, "Output")
			if not os.path.exists(PastaOutput):
				os.makedirs(PastaOutput)
			else:
				for NrPastas in range(1, 10):
					sufixo = "_" + str(NrPastas)
					PastaOutput = os.path.join(InputOutputFolder, "Output" + sufixo)
					if not os.path.exists(PastaOutput):
						os.makedirs(PastaOutput)
						break

		# CRIAR SUBPASTA TABELAS
			PastaTabelas = os.path.join(PastaOutput, "Tabelas")
			os.makedirs(PastaTabelas)

		# CARREGAR VARIAVEL DEPENDENTE E ADICIONAR LAYER AO QGIS
			LoadVarDep = QgsRasterLayer(VarDep, VarDepDisplayName)

			ListaVarIndepVI = []

		# PROPRIEDADES DOS FICHEIROS DE INPUT
			for VarIndep, VarIndepLayerName in zip(ListaVarIndep, ListaLayerName):

			# CARREGAR VARIAVEL INDEPENDENTE E ADICIONAR LAYER AO QGIS
				LoadVarIndep = QgsRasterLayer(VarIndep, VarIndepLayerName)   
				AddVarIndep = QgsMapLayerRegistry.instance().addMapLayer(LoadVarIndep)
				
			# DEFINIR EXTENSAO
				ext = AddVarIndep.extent()
				xmin = ext.xMinimum()
				xmax = ext.xMaximum()
				ymin = ext.yMinimum()
				ymax = ext.yMaximum()
				Mask = "%f,%f,%f,%f" %(xmin, xmax, ymin, ymax)
				
			# DEFINIR CELL SIZE
				PixelSizeX = LoadVarIndep.rasterUnitsPerPixelX()
				PixelSizeY = LoadVarIndep.rasterUnitsPerPixelY()
				CellSize = PixelSizeX*PixelSizeY
				
			# CRIAR REPORT E CALCULAR VALORES UNICOS
				CountUniqueValues = os.path.join(PastaTabelas, VarIndepLayerName + "_CountUniqueValues.txt")
				processing.runalg("grass7:r.report",VarIndep,5,"*",255,True,True,True,True,Mask,None,CountUniqueValues)

				ReportReadLines = open(CountUniqueValues).readlines()
				ReportSelectLines = ReportReadLines[4:-4]
				UniqueValues = len(ReportSelectLines)

			# DEFINIR CAMINHO DO OUTPUT E EXECUTAR R.COIN
				RCoinFile = os.path.join(PastaTabelas, VarIndepLayerName + "_x_" + VarDepDisplayName + "_Original.txt")
				processing.runalg("grass7:r.coin",VarIndep,VarDep,0,False,Mask,None,RCoinFile)

			# LER RCOINFILE E SELECIONAR AS LINHAS COM INFORMACAO UTIL
				ReadLines = open(RCoinFile).readlines()
				SelectLines = ReadLines[22:UniqueValues+22]

			# FORMATAR DADOS PARA IMPORTACAO EM CSV
				ListaValores = []
				for row in SelectLines:
					RemoverEspacos = re.sub(' +',' ',row)
					SubstituirEspacos = RemoverEspacos.replace(' ', ';')
					SepararPontoVirgula = SubstituirEspacos.split(";")
					SelecionarColunas = itemgetter(1,3,5,7)(SepararPontoVirgula)
					JuntarColunas = ';'.join(SelecionarColunas)
					ListaValores.append(JuntarColunas) 	

				if UniqueValues <= 2:
					JuntarLinhas = ';'.join(ListaValores)
					SepararValores = JuntarLinhas.split(";")
					ConversaoInteiros = map(int, SepararValores)
					Linha0 = "V;V0;V1;T\n"
					Linha1 = str(ConversaoInteiros[0]+1) + ";" + str(ConversaoInteiros[1]) + ";" + str(ConversaoInteiros[5]) + ";" + str(ConversaoInteiros[1]+ ConversaoInteiros[5]) + "\n"
					Linha2 = str(ConversaoInteiros[4]+1) + ";" + str(ConversaoInteiros[2]) + ";" + str(ConversaoInteiros[6]) + ";" + str(ConversaoInteiros[2]+ ConversaoInteiros[6])
					ValoresImportar = [Linha0, Linha1, Linha2]
				else: 
					ListaValores.insert(0,'V;V0;V1;T')
					ValoresImportar = '\n'.join(ListaValores)

			# ESCREVER DADOS FORMATADOS NUM NOVO FICHEIRO TXT
				RCoinTemp = os.path.join(PastaTabelas, VarIndepLayerName + "_x_" + VarDepDisplayName + "_Tratado.txt")
				open(RCoinTemp,'wb').writelines(ValoresImportar)

			# IMPORTAR PARA FICHEIRO CSV
				TabulateAreaCSV = os.path.join(PastaTabelas, VarIndepLayerName + "_x_" + VarDepDisplayName + ".csv")
				csv.writer(open(TabulateAreaCSV, 'wb')).writerows(csv.reader(open(RCoinTemp, 'rb')))

			# EXPORTAR PARA DBF
				LoadTabulateAreaCSV = QgsVectorLayer(TabulateAreaCSV, VarIndepLayerName + "_x_" + VarDepDisplayName, "ogr")
				DbfTablePath  = os.path.join(PastaTabelas, VarIndepLayerName + "_x_" + VarDepDisplayName)
				QgsVectorFileWriter.writeAsVectorFormat(LoadTabulateAreaCSV,DbfTablePath,"System",None,"ESRI Shapefile")
				os.remove(DbfTablePath + ".prj")
				os.remove(DbfTablePath + ".qpj")

			# CARREGAR TABELA DBF PARA o QGIS
				DbfTable = QgsVectorLayer(DbfTablePath + ".dbf", VarIndepLayerName + "_x_" + VarDepDisplayName + ".dbf", "ogr")
				AddDbfTable = QgsMapLayerRegistry.instance().addMapLayer(DbfTable)

			# OBTER INDEXs DOS CAMPOS EXISTENTES
				IndexCampoV = DbfTable.fieldNameIndex("V")
				IndexCampoV0 = DbfTable.fieldNameIndex("V0")
				IndexCampoV1 = DbfTable.fieldNameIndex("V1")
				IndexCampoT = DbfTable.fieldNameIndex("T")

			# CRIAR CAMPOS A CALCULAR
				CampoVALUE = DbfTable.dataProvider().addAttributes([QgsField("VALUE", QVariant.Int)])
				CampoVALUE_0 = DbfTable.dataProvider().addAttributes([QgsField("VALUE_0", QVariant.Int)])
				CampoVALUE_1 = DbfTable.dataProvider().addAttributes([QgsField("VALUE_1", QVariant.Int)])
				CampoARCLASSE = DbfTable.dataProvider().addAttributes([QgsField("ARCLASSE", QVariant.Int)])
				CampoPROBCOND = DbfTable.dataProvider().addAttributes([QgsField("PROBCOND", QVariant.Double)])
				CampoSUM_VALUE0 = DbfTable.dataProvider().addAttributes([QgsField("SUM_VALUE0", QVariant.Int)])
				CampoSUM_VALUE1 = DbfTable.dataProvider().addAttributes([QgsField("SUM_VALUE1", QVariant.Int)])
				CampoAR_TOTAL = DbfTable.dataProvider().addAttributes([QgsField("AR_TOTAL", QVariant.Int)])
				CampoPRIORI = DbfTable.dataProvider().addAttributes([QgsField("PRIORI", QVariant.Double)])
				CampoSINI_SN = DbfTable.dataProvider().addAttributes([QgsField("SINI_SN", QVariant.Double)])
				CampoVI = DbfTable.dataProvider().addAttributes([QgsField("VI", QVariant.Double)])
				DbfTable.updateFields()

			# OBTER INDEXs DOS CAMPOS CRIADOS
				IndexCampoVALUE = DbfTable.fieldNameIndex("VALUE")
				IndexCampoVALUE_0 = DbfTable.fieldNameIndex("VALUE_0")
				IndexCampoVALUE_1 = DbfTable.fieldNameIndex("VALUE_1")
				IndexCampoARCLASSE = DbfTable.fieldNameIndex("ARCLASSE")
				IndexCampoPROBCOND = DbfTable.fieldNameIndex("PROBCOND")
				IndexCampoSUM_VALUE0 = DbfTable.fieldNameIndex("SUM_VALUE0")
				IndexCampoSUM_VALUE1 = DbfTable.fieldNameIndex("SUM_VALUE1")
				IndexCampoAR_TOTAL = DbfTable.fieldNameIndex("AR_TOTAL")
				IndexCampoPRIORI = DbfTable.fieldNameIndex("PRIORI")
				IndexCampoSINI_SN = DbfTable.fieldNameIndex("SINI_SN")
				IndexCampoVI = DbfTable.fieldNameIndex("VI")

			# COPIAR VALORES PARA OS CAMPOS BASE
				DbfTable.startEditing()
				for Valores in processing.features(DbfTable):
					DbfTable.changeAttributeValue(Valores.id(), IndexCampoVALUE, Valores[IndexCampoV])
					DbfTable.changeAttributeValue(Valores.id(), IndexCampoVALUE_0, int(Valores[IndexCampoV0])*CellSize)
					DbfTable.changeAttributeValue(Valores.id(), IndexCampoVALUE_1, int(Valores[IndexCampoV1])*CellSize)
					DbfTable.changeAttributeValue(Valores.id(), IndexCampoARCLASSE, int(Valores[IndexCampoT])*CellSize)
				DbfTable.commitChanges()
				DbfTable.updateFields()

				ListaVALUE_0 = []
				ListaVALUE_1 = []
				DbfTable.startEditing()
				for Valores in processing.features(DbfTable):
					DbfTable.changeAttributeValue(Valores.id(), IndexCampoPROBCOND, float(Valores[IndexCampoVALUE_1])/ float(Valores[IndexCampoARCLASSE]))
					ListaVALUE_0.append(int(Valores[IndexCampoVALUE_0]))
					ListaVALUE_1.append(int(Valores[IndexCampoVALUE_1]))
				DbfTable.commitChanges()
				DbfTable.updateFields()

			# CALCULAR CAMPOS 'SUM_VALUE0' e 'SUM_VALUE1'
				SomaVALUE_0 = sum(ListaVALUE_0)
				SomaVALUE_1 = sum(ListaVALUE_1)
				DbfTable.startEditing()
				for Valores in processing.features(DbfTable):
					DbfTable.changeAttributeValue(Valores.id(), IndexCampoSUM_VALUE0, SomaVALUE_0)
					DbfTable.changeAttributeValue(Valores.id(), IndexCampoSUM_VALUE1, SomaVALUE_1)
				DbfTable.commitChanges()
				DbfTable.updateFields()

			# CALCULAR CAMPO 'AR_TOTAL'
				DbfTable.startEditing()
				[DbfTable.changeAttributeValue(Valores.id(), IndexCampoAR_TOTAL, float(Valores[IndexCampoSUM_VALUE0])+ float(Valores[IndexCampoSUM_VALUE1])) for Valores in processing.features(DbfTable)]
				DbfTable.commitChanges()
				DbfTable.updateFields()

			# CALCULAR CAMPO 'PRIORI'
				DbfTable.startEditing()
				[DbfTable.changeAttributeValue(Valores.id(), IndexCampoPRIORI, float(Valores[IndexCampoSUM_VALUE1])/ float(Valores[IndexCampoAR_TOTAL])) for Valores in processing.features(DbfTable)]
				DbfTable.commitChanges()
				DbfTable.updateFields()

			# CALCULAR CAMPO 'SINI_SN'
				DbfTable.startEditing()
				[DbfTable.changeAttributeValue(Valores.id(), IndexCampoSINI_SN, float(Valores[IndexCampoPROBCOND])/ float(Valores[IndexCampoPRIORI])) for Valores in processing.features(DbfTable)]
				DbfTable.commitChanges()
				DbfTable.updateFields()

			# CALCULAR CAMPO 'VI'
				DbfTable.startEditing()
				ListaVI_Min = []
				for Valores in processing.features(DbfTable):
					if float(Valores[IndexCampoSINI_SN]) > 0:
						DbfTable.changeAttributeValue(Valores.id(), IndexCampoVI, math.log(float(Valores[IndexCampoSINI_SN])))
						ListaVI_Min.append(math.log(float(Valores[IndexCampoSINI_SN])))
						ListaVI_Min.sort()
						VI_MIN = (ListaVI_Min [0])
				for Valores in processing.features(DbfTable):
					if float(Valores[IndexCampoSINI_SN]) == 0:
						DbfTable.changeAttributeValue(Valores.id(), IndexCampoVI, float(VI_MIN))	
				DbfTable.commitChanges()
				DbfTable.updateFields()

			# CRIAR EXPRESSAO E FICHEIRO TXT PARA RECLASSIFICACAO COM VALORES DE VI
				ListaReclass = []
				for Valores in processing.features(DbfTable):
					ListaReclass.append(str(Valores[IndexCampoVALUE])+ "=" + str(int(round(Valores[IndexCampoVI], 9)*(10**8))))
				ExpressaoReclass = '\n'.join(ListaReclass)

				ReclassVITxt = os.path.join(PastaTabelas, VarIndepLayerName + "_ReclassVI.txt")
				open(ReclassVITxt,'wb').writelines(ExpressaoReclass)
				

			# RECLASSIFICACAO DAS VARIAVEIS INDEPENDENTES COM VALORES DE VI	
				VarIndepVI = os.path.join(PastaOutput, VarIndepLayerName + "_VI.tif")
				processing.runalg("grass7:r.reclass",VarIndep,ReclassVITxt,Mask,0,VarIndepVI)
				ListaVarIndepVI.append(VarIndepVI)
				
			# APAGAR CAMPOS INICIAIS PROVENIENTES DO CSV
				DbfTable.dataProvider().deleteAttributes([IndexCampoV, IndexCampoV0, IndexCampoV1, IndexCampoT])
				DbfTable.updateFields()
				
			# REMOVER VARIAVEIS INDEPENDENTES DO QGIS
				QgsMapLayerRegistry.instance().removeMapLayers( [AddVarIndep.id()] )
				

		# SOMAR RASTERS DAS VARIAVEIS INDEPENDENTES NO RASTER CALCULATOR PARA OBTER O MAPA VI FINAL
			EntriesVIRaster = []
			ListaVIRasterRef = []
			for Index,VarIndepVI, VarIndepLayerName in zip(range(0, len(ListaVarIndepVI)), ListaVarIndepVI, ListaLayerName):
				LoadVarIndepVI = QgsRasterLayer(VarIndepVI, VarIndepLayerName + "_VI")   
				AddVarIndepVI = QgsMapLayerRegistry.instance().addMapLayer(LoadVarIndepVI)
				VIRasterObject =  processing.getObject(ListaVarIndepVI[Index])
				VIRaster = QgsRasterCalculatorEntry()
				VIRaster.raster = VIRasterObject
				VIRaster.ref = str(VarIndepLayerName + '_VI@1')
				VIRaster.bandNumber = 1
				EntriesVIRaster.append(VIRaster)
				ListaVIRasterRef.append(VIRaster.ref)

			ExpressaoCalculateVI = "(" + " + ".join(ListaVIRasterRef) + ")"
			VI = os.path.join(PastaOutput, "VI.tif")
			CalculateVI = QgsRasterCalculator(ExpressaoCalculateVI, VI, 'GTiff', VIRasterObject.extent(), VIRasterObject.width(), VIRasterObject.height(), EntriesVIRaster)
			CalculateVI.processCalculation()

		# ADICIONAR RASTER DO VALOR INFORMATIVO AO QGIS
			LoadVI = QgsRasterLayer(VI, "VI")
			AddVI = QgsMapLayerRegistry.instance().addMapLayer(LoadVI)

		####VALIDACAO:####

		# CONVERTER RASTER DO VI PARA VALORES INTEIROS
			VIint = os.path.join(PastaOutput, "VIint.tif")
			processing.runalg("gdalogr:rastercalculator",VI,"1",None,"1",None,"1",None,"1",None,"1",None,"1","rint(A)","",4,"",VIint)

		# CRIAR REPORT E CALCULAR VALORES UNICOS DE VI
			VI_CountUniqueValues = os.path.join(PastaTabelas, "VI_CountUniqueValues.txt")
			processing.runalg("grass7:r.report",VIint,5,"*",255,True,True,True,True,Mask,None,VI_CountUniqueValues)

			VI_ReportReadLines = open(VI_CountUniqueValues).readlines()
			VI_ReportSelectLines = VI_ReportReadLines[4:-4]
			VI_UniqueValues = len(VI_ReportSelectLines)

		# DEFINIR CAMINHO DO OUTPUT E EXECUTAR R.COIN DE VALIDACAO
			VI_RCoin = os.path.join(PastaTabelas,"VI_x_" + ValidacaoDisplayName + "_Original.txt")
			processing.runalg("grass7:r.coin",VIint,RasterValidacao,0,False,Mask,None,VI_RCoin)

		# LER VI_RCOIN E SELECIONAR AS LINHAS COM INFORMACAO UTIL
			ValidacaoReadLines = open(VI_RCoin).readlines()
			ValidacaoSelectLines = ValidacaoReadLines[22:VI_UniqueValues+22]

		# FORMATAR DADOS PARA IMPORTACAO EM CSV
			ValidacaoListaValores = []
			for row in ValidacaoSelectLines:
				RemoverEspacos = re.sub(' +',' ',row)
				SubstituirEspacos = RemoverEspacos.replace(' ', ';')
				SepararPontoVirgula = SubstituirEspacos.split(";")
				SelecionarColunas = itemgetter(1,5,7)(SepararPontoVirgula)
				ConversaoInteiros = map(int, SelecionarColunas)
				ValidacaoListaValores.append(ConversaoInteiros) 	
			ValidacaoListaValores = sorted(ValidacaoListaValores, reverse=True)

			ListaOrdenada = []
			for row in ValidacaoListaValores:
				SubstituirEspacos = str(row).replace(', ', ';')
				RemoverParentese1 = SubstituirEspacos.replace('[', '')
				RemoverParentese2 = RemoverParentese1.replace(']', '')
				ListaOrdenada.append(RemoverParentese2)
			ListaOrdenada.insert(0,'V;V1;T')
			ValidacaoValoresImportar = '\n'.join(ListaOrdenada)

		# ESCREVER DADOS FORMATADOS NUM NOVO FICHEIRO TXT
			VI_RCoinTemp = os.path.join(PastaTabelas, "VI_x_" + ValidacaoDisplayName +"_Tratado.txt")
			open(VI_RCoinTemp,'wb').writelines(ValidacaoValoresImportar)

		# IMPORTAR PARA FICHEIRO CSV
			TS_CSV = os.path.join(PastaTabelas, "VI_x_" + ValidacaoDisplayName + ".csv")
			csv.writer(open(TS_CSV, 'wb')).writerows(csv.reader(open(VI_RCoinTemp, 'rb')))

		# EXPORTAR PARA DBF
			LoadTSCSV = QgsVectorLayer(TS_CSV, "TS", "ogr")
			DbfTSPath  = os.path.join(PastaTabelas, "TS")
			QgsVectorFileWriter.writeAsVectorFormat(LoadTSCSV,DbfTSPath,"System",None,"ESRI Shapefile")
			os.remove(DbfTSPath + ".prj")
			os.remove(DbfTSPath + ".qpj")

		# CARREGAR TABELA DBF PARA o QGIS
			DbfTS = QgsVectorLayer(DbfTSPath + ".dbf", "TS.dbf", "ogr")
			AddDbfTS = QgsMapLayerRegistry.instance().addMapLayer(DbfTS)

		# OBTER INDEXs DOS CAMPOS EXISTENTES
			TS_IndexCampoV = DbfTS.fieldNameIndex("V")
			TS_IndexCampoV1 = DbfTS.fieldNameIndex("V1")
			TS_IndexCampoT = DbfTS.fieldNameIndex("T")

		# CRIAR CAMPOS A CALCULAR
			TS_CampoVI = DbfTS.dataProvider().addAttributes([QgsField("VI", QVariant.Double)])
			TS_CampoARESTUDO = DbfTS.dataProvider().addAttributes([QgsField("ARESTUDO", QVariant.Int)])
			TS_CampoARFENOM = DbfTS.dataProvider().addAttributes([QgsField("ARFENOM", QVariant.Int)])
			TS_CampoArEstudAc = DbfTS.dataProvider().addAttributes([QgsField("ArEstudAc", QVariant.Double)])
			TS_CampoArFenomAc = DbfTS.dataProvider().addAttributes([QgsField("ArFenomAc", QVariant.Double)])
			TS_CampoLsi_Li = DbfTS.dataProvider().addAttributes([QgsField("Lsi_Li", QVariant.Double)])
			TS_Campoai_b1_2 = DbfTS.dataProvider().addAttributes([QgsField("ai_b1_2", QVariant.Double)])
			TS_CampoACC = DbfTS.dataProvider().addAttributes([QgsField("ACC", QVariant.Double)])
			DbfTS.updateFields()

		# OBTER INDEXs DOS CAMPOS CRIADOS
			TS_IndexCampoVI = DbfTS.fieldNameIndex("VI")
			TS_IndexCampoARESTUDO = DbfTS.fieldNameIndex("ARESTUDO")
			TS_IndexCampoARFENOM = DbfTS.fieldNameIndex("ARFENOM")
			TS_IndexCampoArEstudAc = DbfTS.fieldNameIndex("ArEstudAc")
			TS_IndexCampoArFenomAc = DbfTS.fieldNameIndex("ArFenomAc")
			TS_IndexCampoLsi_Li = DbfTS.fieldNameIndex("Lsi_Li")
			TS_IndexCampoai_b1_2 = DbfTS.fieldNameIndex("ai_b1_2")
			TS_IndexCampoACC = DbfTS.fieldNameIndex("ACC")

		# COPIAR VALORES PARA OS CAMPOS BASE
			DbfTS.startEditing()
			for Valores in processing.features(DbfTS):
				DbfTS.changeAttributeValue(Valores.id(), TS_IndexCampoVI, float(Valores[TS_IndexCampoV])/ float(10**8))
				DbfTS.changeAttributeValue(Valores.id(), TS_IndexCampoARESTUDO, int(Valores[TS_IndexCampoT])*CellSize)
				DbfTS.changeAttributeValue(Valores.id(), TS_IndexCampoARFENOM, int(Valores[TS_IndexCampoV1])*CellSize)
			DbfTS.commitChanges()
			DbfTS.updateFields()

		# CPRIAR LISTAS DE VALORES PARA AS SOMAS ACUMULADAS
			ListaARESTUDO = []
			ListaARFENOM = []
			for Valores in processing.features(DbfTS):
				ListaARESTUDO.append(int(Valores[TS_IndexCampoARESTUDO]))
				ListaARFENOM.append(int(Valores[TS_IndexCampoARFENOM]))

		# CALCULAR CAMPOS 'ArEstudAc', 'ArFenomAc'
			SomaARESTUDO = sum(ListaARESTUDO)
			SomaARFENOM = sum(ListaARFENOM)
			DbfTS.startEditing()
			for Valores, SomaAcARESTUDO, SomaAcARFENOM in zip(processing.features(DbfTS), numpy.cumsum(ListaARESTUDO), numpy.cumsum(ListaARFENOM)):
				if Valores.id() == 0:
					DbfTS.changeAttributeValue(Valores.id(), TS_IndexCampoArFenomAc, 0)
					DbfTS.changeAttributeValue(Valores.id(), TS_IndexCampoArEstudAc, 0)
				else:
					DbfTS.changeAttributeValue(Valores.id(), TS_IndexCampoArEstudAc, float(SomaAcARESTUDO)/float(SomaARESTUDO))
					DbfTS.changeAttributeValue(Valores.id(), TS_IndexCampoArFenomAc, float(SomaAcARFENOM)/float(SomaARFENOM))
			DbfTS.commitChanges()

		# CALCULAR CAMPOS 'Lsi_Li', 'ai_b1_2'
			ListaArEstudAc = []
			ListaArFenomAc = []
			for Valores in processing.features(DbfTS):
				ListaArEstudAc.append(float(Valores[TS_IndexCampoArEstudAc]))
				ListaArFenomAc.append(float(Valores[TS_IndexCampoArFenomAc]))
			ListaArEstudAc.insert(0,0)
			ListaArFenomAc.insert(0,0)

			DbfTS.startEditing()
			for Valores, ValoresArEstudAc, ValoresArFenomAc in zip(processing.features(DbfTS),ListaArEstudAc, ListaArFenomAc):
				if Valores.id() == 0:
					DbfTS.changeAttributeValue(Valores.id(), TS_IndexCampoLsi_Li, 0)
					DbfTS.changeAttributeValue(Valores.id(), TS_IndexCampoai_b1_2, 0)
				else:
					DbfTS.changeAttributeValue(Valores.id(), TS_IndexCampoLsi_Li, float(Valores[TS_IndexCampoArEstudAc])- float(ValoresArEstudAc))
					DbfTS.changeAttributeValue(Valores.id(), TS_IndexCampoai_b1_2, float(float(Valores[TS_IndexCampoArFenomAc])+ float(ValoresArFenomAc))/float(2))
			DbfTS.commitChanges()

		# CALCULAR CAMPO 'AAC'
			DbfTS.startEditing()
			for Valores in processing.features(DbfTS):
				DbfTS.changeAttributeValue(Valores.id(), TS_IndexCampoACC, float(Valores[TS_IndexCampoai_b1_2])* float(Valores[TS_IndexCampoLsi_Li]))
			DbfTS.commitChanges()

		# SOMAR VALORES DE ACC PARA ESCREVER A MENSAGEM
			ListaACC = []
			for Valores in DbfTS.getFeatures():
				ListaACC.append(Valores[TS_IndexCampoACC])
			SomaACC = round(sum(ListaACC),4)

		# APAGAR CAMPOS INICIAIS PROVENIENTES DO CSV
			DbfTS.dataProvider().deleteAttributes([TS_IndexCampoV, TS_IndexCampoV1, TS_IndexCampoT])
			DbfTS.updateFields()
			
			msgBar = self.iface.messageBar()
			msgBar.pushWidget(msgBar.createMessage("########### O MODELO FOI VALIDADO COM UMA TAXA DE SUCESSO DE " + str(SomaACC) + "! ###########"), QgsMessageBar.INFO) #"...INFO, 5)" para defenir o tempo da mensagem