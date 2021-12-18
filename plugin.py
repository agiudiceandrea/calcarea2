"""
/***************************************************************************
Name                 : Calc Area 2.
Description          : Show the area and length when edit vector layer
Date                 : December, 2021
copyright            : (C) 2021 by Luiz Motta
email                : motta.luiz@gmail.com

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

__author__ = 'Luiz Motta'
__date__ = '2021-12-22'
__copyright__ = '(C) 2021, Luiz Motta'
__revision__ = '$Format:%H$'


import os

from qgis.PyQt.QtCore import QObject, pyqtSlot 
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QToolButton, QMenu

from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsUnitTypes
)
from qgis.gui import QgsMapTool

from .translate import Translate

from .messageoutputhtml import messageOutputHtml

from .calcareaevent import CalcAreaEvent

# from .dialog_setup import DialogSetup


class CalcAreaPlugin(QObject):

    def __init__(self, iface):
        super().__init__()
        self.pluginName = 'Calc Area'
        self.iface = iface
        self.settings = {
            'crs': None,
            'measure': { 'unit_area': None, 'init_length': None}
        }

        self.translate = Translate( type(self).__name__ )
        self.tr = self.translate.tr

        self.actions = {}
        self.toolButton = QToolButton()
        self.toolButton.setMenu( QMenu() )
        self.toolButton.setPopupMode( QToolButton.MenuButtonPopup )
        self.toolBtnAction = self.iface.addToolBarWidget( self.toolButton )
        self.titleTool = self.tr('Show the area and length of layer')

        self.tool = QgsMapTool( iface.mapCanvas() )
        self.toolEvent = CalcAreaEvent( iface )

    def initGui(self):
        def createAction(icon, title, calback, toolTip=None, isCheckable=False):
            action = QAction( icon, title, self.iface.mainWindow() )
            if toolTip:
                action.setToolTip( toolTip )
            action.triggered.connect( calback )
            action.setCheckable( isCheckable )
            self.iface.addPluginToMenu( f"&{self.titleTool}" , action )
            return action

        # Action Tool
        icon = QIcon( os.path.join( os.path.dirname(__file__), 'resources', 'calcarea.svg' ) )
        toolTip = self.tr('Only for editable layers.')
        toolTip = f"{self.titleTool}. *{toolTip}"
        self.actions['tool'] = createAction( icon, self.titleTool, self.runTool, toolTip, True )
        self.tool.setAction( self.actions['tool'] )
        # Action setFields
        title = self.tr('Setup...')
        icon = QgsApplication.getThemeIcon('/propertyicons/general.svg')
        self.actions['measure_field'] = createAction( icon, title, self.runSetup )
        # Action About
        title = self.tr('About...')
        icon = QgsApplication.getThemeIcon('/mActionHelpContents.svg')
        self.actions['about'] = createAction( icon, title, self.runAbout )
        #
        m = self.toolButton.menu()
        for k in self.actions:
            m.addAction( self.actions[ k ] )
        self.toolButton.setDefaultAction( self.actions['tool'] )

    def unload(self):
        for k in self.actions:
            action = self.actions[ k ]
            self.iface.removePluginMenu( f"&{self.titleTool}", action )
            self.iface.removeToolBarIcon( action )
            self.iface.unregisterMainWindowAction( action )
        self.iface.removeToolBarIcon( self.toolBtnAction )

    @pyqtSlot(bool)
    def runTool(self, checked):
        if checked:
            if not self.toolEvent.hasEnable:
                args = {
                    'crs': QgsCoordinateReferenceSystem('EPSG:5641'),
                    'unitArea': QgsUnitTypes.AreaHectares,
                    'unitLength': QgsUnitTypes.DistanceMeters
                }
                self.toolEvent.init( **args)
            return
        
        self.toolEvent.disable()

    @pyqtSlot(bool)
    def runSetup(self, checked):
        pass
        # layer = self.iface.activeLayer()
        # args = (
        #     self.iface.mainWindow(),
        #     self.pluginName
        # )
        # dlg = DialogSetup( *args )
        # if self.currentCrs:
        #     dlg.setCurrentCrs( self.currentCrs )
        # if dlg.exec_() == dlg.Accepted:
        #     self.currentCrs = dlg.currentCrs()

    @pyqtSlot(bool)
    def runAbout(self, checked):
        pass
        # title = self.tr('{} - About')
        # title = title.format( self.pluginName )
        # args = {
        #     'title': title,
        #     'prefixHtml': 'about',
        #     'dirHtml': os.path.join( os.path.dirname(__file__), 'resources' )
        # }
        # messageOutputHtml( **args )

