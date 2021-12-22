# -*- coding: utf-8 -*-
"""
/***************************************************************************
Name                 : Calc Area 2.
Description          : Show layer area and length when editing
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
    QgsUnitTypes
)
from qgis.gui import QgsMapTool

from .translate import Translate

from .messageoutputhtml import messageOutputHtml

from .calcareaevent import CalcAreaEvent

from .dialog_setup import DialogSetup


class CalcAreaPlugin(QObject):
    def __init__(self, iface):
        super().__init__()
        self.pluginName = 'Calc Area 2'
        self.iface = iface
        self.translate = Translate( type(self).__name__ )
        self.tr = self.translate.tr

        self.actions = {}
        self.toolButton = QToolButton()
        self.toolButton.setMenu( QMenu() )
        self.toolButton.setPopupMode( QToolButton.MenuButtonPopup )
        self.toolBtnAction = self.iface.addToolBarWidget( self.toolButton )
        self.toolTip = self.tr('Show layer area and length when editing')
        self.titleTool = 'CalcArea2'

        self.tool = QgsMapTool( iface.mapCanvas() )
        self.toolEvent = CalcAreaEvent( self.iface )
        # self.toolEvent.validLayer.connect( self.actions['tool'].setEnabled ) -> initGui

    def initGui(self):
        def createAction(icon, title, calback, toolTip=None, isCheckable=False):
            action = QAction( icon, title, self.iface.mainWindow() )
            if toolTip:
                action.setToolTip( toolTip )
            action.triggered.connect( calback )
            action.setCheckable( isCheckable )
            self.iface.addPluginToVectorMenu( f"&{self.titleTool}" , action )
            return action

        # Action Tool
        icon = QIcon( os.path.join( os.path.dirname(__file__), 'resources', 'calcarea.svg' ) )
        self.actions['tool'] = createAction( icon, self.titleTool, self.runTool, self.toolTip, True )
        self.tool.setAction( self.actions['tool'] )
        self.toolEvent.validLayer.connect( self.actions['tool'].setEnabled )
        # Action Setup
        title = self.tr('Setup...')
        icon = QgsApplication.getThemeIcon('/propertyicons/general.svg')
        self.actions['setup'] = createAction( icon, title, self.runSetup )
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
            self.iface.removePluginVectorMenu( f"&{self.titleTool}", action )
            self.iface.removeToolBarIcon( action )
            self.iface.unregisterMainWindowAction( action )
        self.iface.removeToolBarIcon( self.toolBtnAction )
        self.toolEvent.validLayer.disconnect( self.actions['tool'].setEnabled )
        del self.toolEvent

    @pyqtSlot(bool)
    def runTool(self, checked):
        self.toolEvent.run( checked )

    @pyqtSlot(bool)
    def runSetup(self, checked):
        settings = self.toolEvent.getCrsUnit()
        layer = self.iface.mapCanvas().currentLayer()
        if not layer is None:
            crs = layer.crs()
            if crs.isValid() and not crs.isGeographic():
                settings['crs'] = crs

        args = settings.copy()
        args['parent'] = self.iface.mainWindow()
        args['title'] = self.pluginName
        dlg = DialogSetup( **args )
        if dlg.exec_() == dlg.Accepted:
            settings = dlg.currentData()
            self.toolEvent.setCrsUnit( settings )

    @pyqtSlot(bool)
    def runAbout(self, checked):
        title = self.tr('{} - About')
        title = title.format( self.pluginName )
        args = {
            'title': title,
            'prefixHtml': 'about',
            'dirHtml': os.path.join( os.path.dirname(__file__), 'resources' )
        }
        messageOutputHtml( **args ) # about_[locale].html

