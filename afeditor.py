﻿#!/usr/bin/env python
# -*- coding: utf-8  -*-

# -------------------------------------------------------------------
# Copyright 2008 Achim Köhler
#
# This file is part of AFMS.
#
# AFMS is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 2 of the License,
# or (at your option) any later version.
#
# AFMS is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with AFMS.  If not, see <http://www.gnu.org/licenses/>.
# -------------------------------------------------------------------

# $Id$

"""
Artefact editor

Artefact editor for managing Features, Requirements, Usecases, Testcases
and Testsuites. This module implements the controller part in the design.

@author: Achim Koehler
@version: $Rev$
"""


import os, sys, time
import logging, gettext, webbrowser
import wx

basepath = os.path.abspath(os.path.dirname(sys.argv[0]))
LOCALEDIR = os.path.join(basepath, 'locale')
DOMAIN = "afms"
gettext.install(DOMAIN, LOCALEDIR, unicode=True)

import _afimages
import afconfig
import afmodel
import _afhelper
from _afartefactlist import *
from _afproductinformation import *
from _aftrashinformation import *
from _affeatureview import *
from _afrequirementview import *
from _aftestcaseview import *
from _afusecaseview import *
from _aftestsuiteview import *
from _afsimplesectionview import *
from _afglossaryentryview import *
from _afmainframe import *
from _afeditartefactdlg import *
import afexporthtml
import afexportxml
import _afimporter
import afresource
import _afclipboard
import _aftagsview
from _afartefact import cChangelogEntry, cTag
import _afbulkview

import _affilterview, _affilter, afdbtoarchive, afarchivetodb, _afstatisticsview

#TODO: validator for features, similar to requirements validator is missing
#TODO: enter key on Feature/Requirement/... in tree should expand the tree
#TODO: empty trash function


class FileDropTarget(wx.FileDropTarget):
    def __init__(self, callback):
        wx.FileDropTarget.__init__(self)
        self.callback = callback


    def OnDropFiles(self, x, y, filenames):
        if len(filenames) > 1: return False
        self.callback(filenames[0])


class EditParams(object):
    iseditmode = False
    parent_id = None
    item_id = None
    editdlg = None
    savedata = None
    simplesectionlevelbtn = None
    callback_onsave = None
    callback_arg = None


def Ignore(*args):
    pass


class MyApp(wx.App):
    """
    wxWidgets main application class.
    """
    def OnInit(self):
        """
        Initialization function called by wxWidgets framework.

        Event binding, class attributes definitions and similar stuff is
        done here.

        @rtype:  boolean
        @return: C{True} on success, C{False} else
        """
        # Read configuration an check for existence of workdir
        self.config = wx.FileConfig(appName="afeditor", vendorName="ka", localFilename="afeditor.cfg", globalFilename="afeditor.gfg", style=wx.CONFIG_USE_LOCAL_FILE|wx.CONFIG_USE_GLOBAL_FILE )
        sp = wx.StandardPaths.Get()
        documents_dir = wx.StandardPaths.GetDocumentsDir(sp)
        workdir = self.config.Read("workdir", documents_dir)
        cssfile = self.config.Read('cssfile', afresource.getDefaultCSSFile())
        self.config.Write('cssfile', cssfile)
        xslfile = self.config.Read('xslfile', afresource.getDefaultXSLFile())
        self.config.Write('xslfile', xslfile)
        if not os.path.exists(workdir):
             self.config.Write("workdir", documents_dir)
        wx.Config.Set(self.config)
        self.editparams = EditParams()
        self.model = afmodel.afModel(self, self.config.Read("workdir", documents_dir))

        # Setup language stuff
        language = self.config.Read("language", 'en')
        afresource.SetLanguage(language)
        wxLanguage = {'de' : wx.LANGUAGE_GERMAN, 'en' : wx.LANGUAGE_ENGLISH}
        try:
            self.wxLanguageCode = wxLanguage[language]
        except KeyError:
            logging.debug('MyApp.OnInit(), language %s unknown' % language)
            self.wxLanguageCode = wx.LANGUAGE_DEFAULT

        try:
            t = gettext.translation(DOMAIN, LOCALEDIR, languages=[language])
            t.install(unicode=True)
        except IOError:
            logging.debug('MyApp.OnInit(), gettext.translation() failed for language %s' % language)
            pass

        self.mainframe = MainFrame(None, "AF Editor")
        dt = FileDropTarget(self._OpenProduct)
        self.mainframe.leftWindow.SetDropTarget(dt)
        self.SetTopWindow(self.mainframe)
        self.mainframe.Show(True)

        self.wildcard = _(afresource.AF_WILDCARD)
        self.htmlwildcard = _(afresource.HTML_WILDCARD)
        self.dont_annoy_at_delete = False
        self.dont_annoy_at_undelete = False
        self.DisableUpdateNodeView = False
        self.DisableOnSelChanged = False

        self.productview = 0
        self.trashview = -1
        self.listview = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14)
        self.trashlistview = self.listview[7:]
        (self.featurelistview, self.requirementlistview,
         self.testcaselistview, self.testsuitelistview, self.usecaselistview,
         self.simplesectionlistview,self.glossaryentrylistview,
         self.trashfeaturelistview, self.trashrequirementlistview,
         self.trashtestcaselistview, self.trashtestsuitelistview,
         self.trashusecaselistview, self.trashsimplesectionlistview,
         self.trashglossaryentrylistview,) = self.listview

        self.singleview = (20, 21, 22, 23, 24, 25, 26)
        (self.featureview, self.requirementview, self.testcaseview,
         self.usecaseview, self.testsuiteview, self.simplesectionview,
         self.glossaryentryview)   = self.singleview

        self.notebooktab = {self.featureview       : 0,  self.requirementview   : 0,
                            self.testcaseview      : 0,  self.usecaseview       : 0,
                            self.testsuiteview     : 0,  self.simplesectionview : 0,
                            self.glossaryentryview : 0}
        self.currentview = None

        self.featurefilterview = _affilterview.afFeatureFilterView(self.mainframe.bottomWindow)
        self.requirementfilterview = _affilterview.afRequirementFilterView(self.mainframe.bottomWindow)
        self.productfilterview = _affilterview.afNoFilterView(self.mainframe.bottomWindow)
        self.nofilterview = self.productfilterview
        self.usecasefilterview = _affilterview.afUsecaseFilterView(self.mainframe.bottomWindow)
        self.testcasefilterview = _affilterview.afTestcaseFilterView(self.mainframe.bottomWindow)
        self.testsuitefilterview = _affilterview.afTestsuiteFilterView(self.mainframe.bottomWindow)
        self.simplesectionfilterview = _affilterview.afSimpleSectionFilterView(self.mainframe.bottomWindow)
        self.glossaryentryfilterview = _affilterview.afNoFilterView(self.mainframe.bottomWindow)

        filterviews = [self.featurefilterview, self.requirementfilterview, self.productfilterview,
            self.testcasefilterview, self.testsuitefilterview, self.usecasefilterview,
            self.simplesectionfilterview, self.glossaryentryfilterview]
        for filterview in filterviews:
            filterview.Hide()
            fid = filterview.btnId
            if fid is None: continue
            self.Bind(wx.EVT_BUTTON, self.ApplyFilterClick, id=fid)
            self.Bind(wx.EVT_BUTTON, self.ApplyFilterClick, id=fid+1)

        self.PARENTID = afresource.ARTEFACTLIST

        self.filterstate = {}
        for item in self.PARENTID:
            self.filterstate[item] = False

        self.delfuncs = (self.model.deleteFeature, self.model.deleteRequirement,
            self.model.deleteUsecase, self.model.deleteTestcase,
            self.model.deleteTestsuite, self.model.deleteSimpleSection, self.model.deleteGlossaryEntry)

        self.getfuncs = (self.model.getFeature, self.model.getRequirement,
                         self.model.getUsecase, self.model.getTestcase,
                         self.model.getTestsuite, self.model.getSimpleSection,
                         self.model.getGlossaryEntry)

        self.Bind(wx.EVT_MENU, self.OnNewProduct, id=101)
        self.Bind(wx.EVT_MENU, self.OnOpenProduct, id=102)
        self.Bind(wx.EVT_MENU, self.OnExportHTML, id=103)
        self.Bind(wx.EVT_MENU, self.OnExportXML, id=104)
        self.Bind(wx.EVT_MENU, self.OnImport, id=105)
        self.Bind(wx.EVT_MENU, self.OnViewStatistics, id=106)
        self.Bind(wx.EVT_MENU_RANGE, self.OnFileHistory, id=wx.ID_FILE1, id2=wx.ID_FILE9)

        self.Bind(wx.EVT_MENU, self.OnEditArtefact, id = 201)
        self.Bind(wx.EVT_MENU, self.OnDeleteArtefact, id = 202)
        self.Bind(wx.EVT_MENU, self.copyArtefactToClipboard, id = 203)
        self.Bind(wx.EVT_MENU, self.pasteArtefactFromClipboard, id = 204)
        self.Bind(wx.EVT_MENU, self.OnEditTags, id = 205)

        self.Bind(wx.EVT_MENU, self.OnNewFeature, id = 301)
        self.Bind(wx.EVT_MENU, self.OnNewRequirement, id = 302)
        self.Bind(wx.EVT_MENU, self.OnNewTestcase, id = 303)
        self.Bind(wx.EVT_MENU, self.OnNewTestsuite, id = 304)
        self.Bind(wx.EVT_MENU, self.OnNewUsecase, id = 305)
        self.Bind(wx.EVT_MENU, self.OnNewSimpleSection, id = 306)
        self.Bind(wx.EVT_MENU, self.OnAddGlossaryEntry, id=307)

        self.Bind(wx.EVT_MENU, self.OnDatabaseToArchive, id = 401)
        self.Bind(wx.EVT_MENU, self.OnArchiveToDatabase, id = 402)

        self.Bind(wx.EVT_TOOL, self.OnNewProduct, id=10)
        self.Bind(wx.EVT_TOOL, self.OnOpenProduct, id=11)
        self.Bind(wx.EVT_TOOL, self.OnEditArtefact, id=12)
        self.Bind(wx.EVT_TOOL, self.copyArtefactToClipboard, id=30)
        self.Bind(wx.EVT_TOOL, self.pasteArtefactFromClipboard, id=31)
        self.Bind(wx.EVT_TOOL, self.OnDeleteArtefact, id=18)
        self.Bind(wx.EVT_TOOL, self.OnNewFeature, id=13)
        self.Bind(wx.EVT_TOOL, self.OnNewRequirement, id=14)
        self.Bind(wx.EVT_TOOL, self.OnNewUsecase, id=17)
        self.Bind(wx.EVT_TOOL, self.OnNewTestcase, id=15)
        self.Bind(wx.EVT_TOOL, self.OnNewTestsuite, id=16)
        self.Bind(wx.EVT_TOOL, self.OnNewSimpleSection, id=19)
        self.Bind(wx.EVT_TOOL, self.OnAddGlossaryEntry, id=20)

        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelChanged, id=300)
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnTreeItemActivated, id=301)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnListItemActivated)

        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnPageChanged)

        self.Bind(wx.EVT_BUTTON, self.OnSimpleSectionLevelChanged, id=5137)

        global arguments
        if len(arguments) > 0:
            try:
                self.OpenProduct(arguments[0])
            except IOError:
                print(_("Could not open file %s")% arguments[0])
                sys.exit(2)

        return True


    def OnDatabaseToArchive(self, evt):
        defaultFile = os.path.splitext(self.model.getFilename())[0] + ".xml"
        dlg = wx.FileDialog(
            self.mainframe, message = _("Save archive as"),
            defaultDir = self.model.currentdir,
            defaultFile = defaultFile,
            wildcard = afresource.XML_WILDCARD,
            style=wx.SAVE | wx.OVERWRITE_PROMPT
            )
        dlgResult = dlg.ShowModal()
        if  dlgResult == wx.ID_OK:
            path = dlg.GetPath()
        dlg.Destroy()
        if  dlgResult == wx.ID_OK:
            try:
                afdbtoarchive.afdbtoarchive(self.model.getFilename(), path)
            except:
                _afhelper.ExceptionMessageBox(sys.exc_info(), _('Error saving archive'))
                logging.error(str(sys.exc_info()))


    def OnArchiveToDatabase(self, evt):
        dlg = _afhelper.ArchiveToDBDialog(self.mainframe)
        dlgResult = dlg.ShowModal()
        (archive_filename, database_filename, openflag) = dlg.GetValue()
        dlg.Destroy()
        if  dlgResult == wx.ID_OK:
            try:
                self.mainframe.SetCursor(wx.HOURGLASS_CURSOR)
                afarchivetodb.afarchivetodb(archive_filename, database_filename)
                if openflag:
                    self.OpenProduct(database_filename)
            except:
                _afhelper.ExceptionMessageBox(sys.exc_info(), _('Error converting archive'))
                logging.error(str(sys.exc_info()))
            self.mainframe.SetCursor(wx.STANDARD_CURSOR)


    def OnViewStatistics(self, evt):
        statisticdata = []

        funcs = [self.model.getIDofFeaturesWithoutRequirements, self.model.getIDofRequirementsWithoutTestcases,
                 self.model.getIDofTestcasesWithoutRequirements, self.model.getIDofTestcasesWithoutTestsuites,
                 self.model.getIDofTestsuitesWithoutTestcases, self.model.getIDofUsecasesWithoutArtefacts]
        keys = [_('Features without requirements'), _('Requirements without test cases'),
                _('Test cases without requirements'), _('Test cases without test suites'),
                _('Test suites without test cases'), _('Usecases without features or requirements')]
        for func, key in zip(funcs, keys):
            idlist = func()
            if len(idlist) > 0:
                imageindex = 1
                value = '%d (%s)' % (len(idlist), ','.join([str(id) for id in idlist]))
            else:
                imageindex = 0
                value = '0'
            sd = _afstatisticsview.StatisticData(key, value, imageindex)
            statisticdata.append(sd)

        funcs = [self.model.getSimpleSectionIDs, self.model.getGlossaryEntryIDs,
                 self.model.getFeatureIDs, self.model.getRequirementIDs,
                 self.model.getUsecaseIDs, self.model.getTestcaseIDs,
                 self.model.getTestsuiteIDs]
        keys = [_('Text sections'), _('Glossary entries'),
                _('Features'), _('Requirements'),
                _('Use cases'), _('Test cases'), _('Test suites')]
        for func, key in zip(funcs, keys):
            idlist = func()
            if len(idlist) > 0:
                imageindex = 0
            else:
                imageindex = 1
            value = str(len(idlist))
            sd = _afstatisticsview.StatisticData(key, value, imageindex)
            statisticdata.append(sd)

        dlg = _afstatisticsview.StatisticsDialog(self.mainframe, -1)
        dlg.InitContent(statisticdata)
        dlg.ShowModal()


    def OnEditTags(self, evt):
        dlg = _aftagsview.afTagListEditor(self.mainframe)
        dlg.InitContent(afconfig.TAGLIST)
        if dlg.ShowModal() == wx.ID_SAVE:
            afconfig.TAGLIST = dlg.GetContent()
            self.model.saveTaglist(afconfig.TAGLIST)
            self.mainframe.treeCtrl.UpdateItemColors()
            self.InitFilters()
        dlg.Destroy()


    def OnSimpleSectionLevelChanged(self, evt):
        self.model.assignSimpleSectionLevels(evt.GetClientData())
        self.InitView()
        self.mainframe.treeCtrl.SetSelection('SIMPLESECTIONS')


    def OnAddGlossaryEntry(self, evt):
        self.requestEditView("GLOSSARYENTRIES", -1)


    def ApplyFilterClick(self, evt):
        self.InitView()
        self.DisableUpdateNodeView = True
        evtdata = evt.GetClientData()
        self.filterstate[evtdata['aftype']] = evtdata['state']
        self.mainframe.treeCtrl.SetSelection(evtdata['aftype'])
        self.mainframe.SetFilterInfo(self.filterstate)


    def copyArtefactToClipboard(self, evt=None):
        (parent_id, item_id) = self.mainframe.treeCtrl.GetSelectedItem()
        if parent_id == "PRODUCT":
            # a list is shown in the right panel, get ID of selected item
            (parent_id, item_id) = self.contentview.GetSelectionID()
        if parent_id is None: return
        if parent_id.startswith('TRASH'): return
        if item_id is None: return

        logging.debug("afeditor.MyApp.copyArtefactToClipboard(): %s" % str((parent_id, item_id)))

        try:
            idx = [item['id'] for item in afresource.ARTEFACTS].index(parent_id)
        except ValueError:
            return

        artefact = [self.model.getFeature, self.model.getRequirement, self.model.getUsecase,
                   self.model.getTestcase, self.model.getTestsuite, self.model.getSimpleSection,
                   self.model.getGlossaryEntry][idx](item_id)

        copytoclip = [_afclipboard.copyFeatureToClipboard, _afclipboard.copyRequirementToClipboard,
                      _afclipboard.copyUsecaseToClipboard, _afclipboard.copyTestcaseToClipboard,
                      _afclipboard.copyTestsuiteToClipboard, _afclipboard.copySimpleSectionToClipboard,
                      _afclipboard.copyGlossaryEntryToClipboard][idx]
        copytoclip(artefact)


    def pasteArtefactFromClipboard(self, evt=None):
        # Well, I know here is a lot of repeated code
        # But I think this makes it better understandable
        (af_kind, afobj) = _afclipboard.getArtefactFromClipboard()
        if af_kind is None:
            return

        self.DisableUpdateNodeView = True
        afobj['ID'] = -1 # it is a new artefact
        cle = cChangelogEntry(user=afconfig.CURRENT_USER, description='', changetype=0, date=time.strftime(afresource.TIME_FORMAT))
        afobj.setChangelog(cle)

        if af_kind == 'AFMS_FEATURE':
            (data, new_artefact) = self.model.saveFeature(afobj)
            if self.currentview == self.featurelistview:
                self.contentview.AppendItem(data)
            self.updateView([wx.ID_OK, new_artefact, data, None], 'FEATURES', -1)

        elif af_kind == 'AFMS_REQUIREMENT':
            (data, new_artefact) = self.model.saveRequirement(afobj)
            if self.currentview == self.requirementlistview:
                # reformat basedata to fit into the list view
                self.contentview.AppendItem(data)
            self.updateView([wx.ID_OK, new_artefact, data, None], 'REQUIREMENTS', -1)

        elif af_kind == 'AFMS_USECASE':
            (data, new_artefact) = self.model.saveUsecase(afobj)
            if self.currentview == self.usecaselistview:
                self.contentview.AppendItem(data)
            self.updateView([wx.ID_OK, new_artefact, data, None], 'USECASES', -1)

        elif af_kind == 'AFMS_TESTCASE':
            (data, new_artefact) = self.model.saveTestcase(afobj)
            if self.currentview == self.testcaselistview:
                # reformat basedata to fit into the list view
                self.contentview.AppendItem(data)
            self.updateView([wx.ID_OK, new_artefact, data, None], 'TESTCASES', -1)

        elif af_kind == 'AFMS_TESTSUITE':
            (data, new_artefact) = self.model.saveTestsuite(afobj)
            if self.currentview == self.testsuitelistview:
                # reformat data to the same format as it is returned by self.model.getTestsuiteList()
                self.contentview.AppendItem(data)
            self.updateView([wx.ID_OK, new_artefact, data, None], 'TESTSUITES', -1)

        elif af_kind == 'AFMS_SIMPLESECTION':
            (data, new_artefact) = self.model.saveSimpleSection(afobj)
            if self.currentview == self.simplesectionlistview:
                # reformat data to the same format as it is returned by self.model.getSimpleSectionList()
                self.contentview.AppendItem(data)
            self.updateView([wx.ID_OK, new_artefact, data, None], 'SIMPLESECTIONS', -1)

        elif af_kind == 'AFMS_GLOSSARYENTRY':
            (data, new_artefact) = self.model.saveGlossaryEntry(afobj)
            if self.currentview == self.glossaryentrylistview:
                # reformat data to the same format as it is returned by self.model.getGlossaryEntryList()
                self.contentview.AppendItem(data)
            self.updateView([wx.ID_OK, new_artefact, data, None], 'GLOSSARYENTRIES', -1)


    def OnPageChanged(self, evt):
        """
        Event handler function called when a notebook page has changed.
        @type  evt: wx.NotebookEvent
        @param evt: event data
        """
        self.notebooktab[self.currentview] = evt.GetSelection()


    def OnFileHistory(self, evt):
        fileNum = evt.GetId() - wx.ID_FILE1
        path = self.mainframe.filehistory.GetHistoryFile(fileNum)
        try:
            self.OpenProduct(path)
            # add it back to the history so it will be moved up the list
            self.mainframe.filehistory.AddFileToHistory(path)
        except:
            _afhelper.ExceptionMessageBox(sys.exc_info(), _('Error opening product!'))
            self.mainframe.filehistory.RemoveFileFromHistory(fileNum)


    def OnNewProduct(self, evt):
        """
        Event handler for menu item or toolbar item 'New Product'.
        @type  evt: wx.CommandEvent
        @param evt: event data
        """
        dlg = wx.FileDialog(
            self.mainframe, message = _("Save new product to file"),
            defaultDir = self.model.currentdir,
            defaultFile = "",
            wildcard = self.wildcard,
            style=wx.SAVE | wx.CHANGE_DIR | wx.OVERWRITE_PROMPT
            )
        dlgResult = dlg.ShowModal()
        if  dlgResult == wx.ID_OK:
            path = dlg.GetPath()
        dlg.Destroy()
        if  dlgResult == wx.ID_OK:
            try:
                self.model.requestNewProduct(path)
                self.InitView()
                afconfig.TAGLIST = self.model.getTaglist()
                afconfig.basedir = os.path.dirname(self.model.getFilename())
                self.mainframe.filehistory.AddFileToHistory(path)
            except:
                _afhelper.ExceptionMessageBox(sys.exc_info(), _('Error creating product'))
                logging.error(str(sys.exc_info()))


    def OnOpenProduct(self, evt):
        """
        Event handler for menu item or toolbar item 'Open Product'.
        @type  evt: wx.CommandEvent
        @param evt: event data
        """
        dlg = wx.FileDialog(
            self.mainframe, message = _("Open product file"),
            defaultDir = self.model.currentdir,
            defaultFile = "",
            wildcard = self.wildcard,
            style=wx.OPEN | wx.CHANGE_DIR | wx.FILE_MUST_EXIST
            )
        dlgResult = dlg.ShowModal()
        if  dlgResult == wx.ID_OK:
            path = dlg.GetPath()
        dlg.Destroy()
        if  dlgResult == wx.ID_OK:
            self._OpenProduct(path)


    def _OpenProduct(self, path):
        try:
            self.OpenProduct(path)
            self.mainframe.filehistory.AddFileToHistory(path)
        except:
            _afhelper.ExceptionMessageBox(sys.exc_info(), _('Error opening product!'))


    def OpenProduct(self, path):
        """
        Open product database file.
        @type  path: string
        @param path: Path of product database file
        """
        self.model.requestOpenProduct(path)
        afconfig.TAGLIST = self.model.getTaglist()
        self.InitFilters()
        self.InitView()
        afconfig.basedir = os.path.dirname(self.model.getFilename())


    def InitFilters(self):
        flt = _affilter.afFeatureFilter()
        flt.SetChangedByList(self.model.requestChangersList())
        flt.SetVersionList(self.model.requestVersionList('FEATURES'))
        self.featurefilterview.InitFilterContent(flt)

        flt = _affilter.afRequirementFilter()
        flt.SetChangedByList(self.model.requestChangersList())
        flt.SetVersionList(self.model.requestVersionList('REQUIREMENTS'))
        flt.SetAssignedList(self.model.requestAssignedList())
        self.requirementfilterview.InitFilterContent(flt)

        flt = _affilter.afUsecaseFilter()
        flt.SetChangedByList(self.model.requestChangersList())
        flt.SetActorsList(self.model.requestActorList())
        flt.SetStakeholdersList(self.model.requestStakeholderList())
        self.usecasefilterview.InitFilterContent(flt)

        flt = _affilter.afTestcaseFilter()
        flt.SetChangedByList(self.model.requestChangersList())
        flt.SetVersionList(self.model.requestVersionList('TESTCASES'))
        self.testcasefilterview.InitFilterContent(flt)

        flt = _affilter.afTestsuiteFilter()
        self.testsuitefilterview.InitFilterContent(flt)

        flt = _affilter.afSimpleSectionFilter()
        self.simplesectionfilterview.InitFilterContent(flt)


    def InitView(self):
        path = self.model.getFilename()
        filters = [ self.featurefilterview.GetFilterContent(),
                    self.requirementfilterview.GetFilterContent(),
                    self.usecasefilterview.GetFilterContent(),
                    self.testcasefilterview.GetFilterContent(),
                    self.testsuitefilterview.GetFilterContent(),
                    self.simplesectionfilterview.GetFilterContent(),
                    self.glossaryentryfilterview.GetFilterContent()]
        artefactinfo = self.model.getArtefactNames(filters)
        number_of_deleted_artefacts = self.model.getNumberOfDeletedArtefacts()
        self.DisableOnSelChanged = True
        self.mainframe.InitView(path, artefactinfo, number_of_deleted_artefacts)
        self.updateNodeView(None, "PRODUCT")
        self.DisableOnSelChanged = False


    def OnEditArtefact(self, evt):
        """
        Command 'Edit feature' or similar has been issued by menu or toolbat.
        @type  evt: wx.CommandEvent
        @param evt: event data
        """
        logging.debug("afeditor.OnEditArtefact(), self.currentview=%s" % self.currentview)
        item = self.mainframe.treeCtrl.GetSelection()
        if not item: return

        (parent_id, item_id) = self.mainframe.treeCtrl.GetItemInfo(item)
        if parent_id == "TRASH": return
        if parent_id == "PRODUCT":
            # a list is shown, we want to edit the item selected in the list
            try:
                (tree_parent_id, tree_item_id) = (parent_id, item_id)
                (parent_id, item_id) = self.contentview.GetSelectionID()
            except:
                # no item selected in the list
                return
        elif item_id == 'PRODUCT':
            pass
        elif parent_id is None:
            return

        self.requestEditView(parent_id, item_id)
        logging.debug("afeditor.OnEditArtefact() done")


    def OnTreeItemActivated(self, evt):
        """
        Item in product tree has been activated by double click or return key
        This is handled as request to edit the item.
        @type  evt: wx.TreeEvent
        @param evt: event data
        """
        self.OnEditArtefact(None)


    def OnDeleteArtefact(self, evt):
        """
        The menu item or toolbar item 'Delete Artefact' was issued
        @type  evt: wx.CommandEvent
        @param evt: event data
        """
        logging.debug("afeditor.OnDeleteArtefact()")
        delete_from_list = False
        item = self.mainframe.treeCtrl.GetSelection()
        if not item: return

        (parent_id, item_id) = self.mainframe.treeCtrl.GetItemInfo(item)
        if parent_id == "TRASH": return
        if parent_id == "PRODUCT":
            # a list is shown, we want to delete the item selected in the list
            try:
                (tree_parent_id, tree_item_id) = (parent_id, item_id)
                delete_from_list = True
                (parent_id, item_id) = self.contentview.GetSelectionID()
            except:
                # no item selected in the list
                return
        elif parent_id is None:
            return

        if not self.dont_annoy_at_delete:
            (retval, self.dont_annoy_at_delete) = _afhelper.DontAnnoyMessageBox(_("Really delete artefact?"), _("Delete artefact"))
            if retval != wx.ID_YES: return

        artefact = self.getfuncs[self.PARENTID.index(parent_id)](item_id)
        if artefact.supportsChangelog():
            (retval, changelogentry) = _afhelper.ChangelogEntryMessageBox(_("Enter changelog"))
            if retval != wx.ID_OK: return
        else:
            changelogentry = None

        try:
            self.delfuncs[self.PARENTID.index(parent_id)](item_id, changelogentry=changelogentry)

            (wxTreeParentId, wxTreeChildId) = self.mainframe.treeCtrl.FindItem(parent_id, item_id)
            self.mainframe.treeCtrl.Delete(wxTreeChildId)

            self.mainframe.treeCtrl.UpdateTrashIcons(self.model.getNumberOfDeletedArtefacts())

            if delete_from_list is True:
                # Update artefact list in right panel
                self.DisableUpdateNodeView = True
                self.contentview.DeleteSelectedItem()
                self.mainframe.treeCtrl.SelectItem(wxTreeParentId)
                self.mainframe.rightWindow.SetFocus()
                self.contentview.SetFocus()
        except:
            _afhelper.ExceptionMessageBox(sys.exc_info())


    def OnExportHTML(self, evt):
        """
        Export database to HTML file
        @type  evt: wx.CommandEvent
        @param evt: event data
        """
        dlg = wx.FileDialog(
            self.mainframe, message = _("Save HTML to file"),
            defaultDir = self.model.currentdir,
            defaultFile = os.path.splitext(self.model.getFilename())[0] + ".html",
            wildcard = self.htmlwildcard,
            style=wx.SAVE | wx.OVERWRITE_PROMPT
            )
        dlgResult = dlg.ShowModal()
        if  dlgResult == wx.ID_OK:
            path = dlg.GetPath()
        dlg.Destroy()
        if  dlgResult == wx.ID_OK:
            try:
                stylesheet = self.config.Read('cssfile', afresource.getDefaultCSSFile())
                afexporthtml.doExportHTML(path, self.model, stylesheet)
                openhtmlreport = self.config.ReadBool('autoopenhtmlreport', False)
                if openhtmlreport:
                    webbrowser.open(url=path, new=2)
            except:
                _afhelper.ExceptionMessageBox(sys.exc_info(), 'Error exporting to HTML!')


    def OnExportXML(self, evt):
        """
        Export database to XML file
        @type  evt: wx.CommandEvent
        @param evt: event data
        """
        dlg = wx.FileDialog(
            self.mainframe, message = _("Save XML to file"),
            defaultDir = self.model.currentdir,
            defaultFile = os.path.splitext(self.model.getFilename())[0] + ".xml",
            wildcard = _(afresource.XML_WILDCARD),
            style=wx.SAVE | wx.OVERWRITE_PROMPT
            )
        dlgResult = dlg.ShowModal()
        if  dlgResult == wx.ID_OK:
            path = dlg.GetPath()
        dlg.Destroy()
        if  dlgResult == wx.ID_OK:
            try:
                stylesheet = self.config.Read('xslfile', afresource.getDefaultXSLFile())
                afexportxml.doExportXML(path, self.model, stylesheet)
                openxmlreport = self.config.ReadBool('autoopenxmlreport', False)
                if openxmlreport:
                    webbrowser.open(url=path, new=2)
            except:
                _afhelper.ExceptionMessageBox(sys.exc_info(), 'Error exporting to XML!')


    def GetParentAndItemID(self):
        """
        Figure out which item is currently selected, either in the left panel tree
        or in an artefact list in the right panel.
        """
        (parent_id, item_id) = (None, None)
        treeitem = self.mainframe.treeCtrl.GetCurrentItem()
        if treeitem:
            (parent_id, item_id) = self.mainframe.treeCtrl.GetItemInfo(treeitem)
        if not treeitem or parent_id == "PRODUCT":
            # no selection in left tree or list in right panel,
            # so lock for an artefact list in the right panel
            try:
                (parent_id, item_id) = self.contentview.GetSelectionID()
            except:
                pass
        return (parent_id, item_id)


    def OnNewFeature(self, evt):
        """
        The menu item or toolbar item 'New Feature' was issued
        @type  evt: wx.CommandEvent
        @param evt: event data
        """
        self.requestEditView("FEATURES", -1)


    def OnNewRequirement(self, evt):
        """
        The menu item or toolbar item 'New Requirement' was issued
        @type  evt: wx.CommandEvent
        @param evt: event data

        If a featue is selected and the 'New Requirement' command is issued
        then the new requirement will be attached to the selected feature.
        """
        # Get the current selected item when the new command is issued
        (parent_id, item_id) = self.GetParentAndItemID()
        if (parent_id != "FEATURES"):
            self.requestEditView("REQUIREMENTS", -1)
        else:
            self.requestEditView("REQUIREMENTS", -1,
                                 callback_onsave=lambda af, item_id: self.model.addFeatureRequirementRelation(item_id, af['ID']),
                                 callback_arg=item_id)


    def OnNewTestcase(self, evt):
        """
        The menu item or toolbar item 'New Testcase' was issued
        @type  evt: wx.CommandEvent
        @param evt: event data

        If a requirement or a testsuite is selected and the 'New Testcase'
        command is issued then the new testcase will be attached to the selected
        requirement or testsuite.
        """
        # Get the current selected item when the new command is issued
        (parent_id, item_id) = self.GetParentAndItemID()
        if (parent_id == "REQUIREMENTS"):
            f = lambda af, item_id: self.model.addRequirementTestcaseRelation(item_id, af['ID'])
        elif (parent_id == "TESTSUITES"):
            f = lambda af, item_id: self.model.addTestsuiteTestcaseRelation(item_id, af['ID'])
        else:
            f = Ignore
        self.requestEditView("TESTCASES", -1, callback_onsave=f, callback_arg=item_id)


    def OnNewUsecase(self, evt):
        """
        The menu item or toolbar item 'New Usecase' was issued
        @type  evt: wx.CommandEvent
        @param evt: event data

        If a requirement is selected and the 'New Usecase' command is issued
        then the new usecase will be attached to the selected requirement.
        """
        # Get the current selected item when the new command is issued
        (parent_id, item_id) = self.GetParentAndItemID()
        if (parent_id == "REQUIREMENTS"):
            f = lambda af, item_id: self.model.addRequirementUsecaseRelation(item_id, af['ID'])
        elif (parent_id == "FEATURES"):
            f =lambda af, item_id: self.model.addFeatureUsecaseRelation(item_id, af['ID'])
        else:
            f = Ignore
        self.requestEditView("USECASES", -1, callback_onsave=f, callback_arg=item_id)


    def OnNewTestsuite(self, evt):
        """
        The menu item or toolbar item 'New Testsuite' was issued
        @type  evt: wx.CommandEvent
        @param evt: event data
        """
        self.requestEditView("TESTSUITES", -1)


    def OnNewSimpleSection(self, evt):
        """
        The menu item or toolbar item 'New text section' was issued
        @type  evt: wx.CommandEvent
        @param evt: event data
        """
        self.requestEditView("SIMPLESECTIONS", -1)


    def OnSelChanged(self, evt):
        """
        The selection in the product tree has changed
        @type  evt: wx.TreeEvent
        @param evt: event data
        """
        if self.DisableOnSelChanged: return
        logging.debug("afeditor.OnSelChanged()")
        item = evt.GetItem()
        if item:
            (parent_id, item_id) = self.mainframe.treeCtrl.GetItemInfo(item)
            self.updateNodeView(parent_id, item_id)
            self.mainframe.treeCtrl.SetFocus()


    def OnListItemActivated(self, evt):
        """
        An item in the feature/requirement/... list has been activated
        @type  evt: wx.ListEvent
        @param evt: event data
        """
        logging.debug("afeditor.OnListItemActivated(), self.currentview=%s" % self.currentview)
        (parent_id, item_id) = self.contentview.GetSelectionID()
        if self.currentview in self.trashlistview:
            self.undeleteArtefact(parent_id, item_id)
        else:
            self.requestEditView(parent_id, item_id)


    def ViewProductInfo(self, product_info):
        """
        Display product information in the right panel
        @type  product_info: nested tuple
        @param product_info: Product data
        """
        self.currentview = self.productview
        self.contentview = self.mainframe.AddContentView(afProductInformation)
        self.contentview.InitContent(product_info)


    def ViewTrashInfo(self, trash_info):
        """
        Display trash information in the right panel
        @type  trash_info: dictionary
        @param trash_info: Dictionary with artefact names as keys and number of deleted
                           artefacts as values
        """
        self.currentview = self.trashview
        self.contentview = self.mainframe.AddContentView(afTrashInformation)
        self.contentview.InitContent(trash_info)


    def ViewArtefactList(self, _contentview, _currentview, artefact_list, select_id=0):
        """
        Display list with all artefacts of a certain category in the right panel
        @type   _contentview: list view object
        @param  _contentview: Object to display artefact list
        @type   _currentview: integer
        @param  _currentview: flag for current view
        @type  artefact_list: tuple list
        @param artefact_list: List with artefact objects
        @type      select_id: integer
        @param     select_id: Item to be selected in the list, 0 means none
        """
        self.currentview = _currentview
        self.contentview = self.mainframe.AddContentView(_contentview)
        self.contentview.InitContent(artefact_list, select_id)


    def ViewArtefact(self, data, _contentview, _currentview):
        """
        Display certain artefact in the right panel
        @type           data: object
        @param           data: artefact objects
        @type   _contentview: view object
        @param  _contentview: Object to display artefact
        @type   _currentview: integer
        @param  _currentview: flag for current view
        """
        self.currentview = None
        contentview = self.mainframe.AddContentView(_contentview)
        self.currentview = _currentview
        contentview.ChangeSelection(self.notebooktab[self.currentview])
        contentview.InitContent(data)


    def EditProductInfo(self, product_info):
        """
        Edit product information in dialog window
        @type  product_info: nested tuple
        @param product_info: Product data
        """
        dlg = EditArtefactDialog(self.mainframe.rightWindow, -1, title=_("Edit Product"), contentview = afProductInformation)
        dlg.contentview.InitContent(product_info)
        dlgResult = dlg.ShowModal()
        if dlgResult == wx.ID_SAVE:
            product_info = dlg.contentview.GetContent()
            self.model.saveProductInfo(product_info)
            self.ViewProductInfo(product_info)


    def EditFeature(self, feature):
        """
        Edit feature data in dialog window
        @type  feature: object
        @param feature: Feature object
        @rtype:  nested tuple
        @return: same as L{EditArtefact}
        """
        feature.validator =  self.validateArtefact
        afconfig.VERSION_NAME = self.model.requestVersionList('FEATURES')
        self.EditArtefact(_("Edit feature"), afFeatureNotebook, self.model.saveFeature, feature)


    def EditRequirement(self, requirement):
        """
        Edit requirement data in dialog window
        @type  requirement: object
        @param requirement: Requirement object
        @rtype:  nested tuple
        @return: same as L{EditArtefact}
        """
        logging.debug("afeditor.EditRequirement()")
        afconfig.ASSIGNED_NAME = self.model.requestAssignedList()
        afconfig.VERSION_NAME = self.model.requestVersionList('REQUIREMENTS')
        requirement.validator = self.validateArtefact
        self.EditArtefact(_("Edit requirement"), afRequirementNotebook, self.model.saveRequirement, requirement)


    def validateArtefact(self, initial_requirement, current_requirement):
        """
        Validate an edited requirement or feature
        @type initial_basedata  : tuple
        @param initial_basedata : requirement/feature basedata before editing
        @type current_basedata  : tuple
        @param current_basedata : requirement/feature basedata after editing
        @type changelog         : tuple
        @param changelog        : changelog data
        @rtype                  : tuple
        @return                 : Validation result and optional error message
                                  - result 0 means everything okay
                                  - result 1 and 2 means validation failed
        """
        initial_status = initial_requirement['status']
        current_status = current_requirement['status']
        changelog_text = current_requirement.getChangelog()['description']
        if initial_status == afresource.STATUS_APPROVED and current_status == afresource.STATUS_APPROVED and len(changelog_text) <= 0:
            return (1, _("Artefact is already approved!\nChangelog description is required."))
        if initial_status == afresource.STATUS_COMPLETED and current_status == afresource.STATUS_COMPLETED:
            return (2, _("Artefact is already completed!\nChanges are prohibited!"))
        return (0, None)


    def EditTestcase(self, testcase):
        """
        Edit testcase data in dialog window
        @type  testcase: object
        @param testcase: Testcase object
        @rtype:  nested tuple
        @return: same as L{EditArtefact}
        """
        afconfig.VERSION_NAME = self.model.requestVersionList('TESTCASES')
        self.EditArtefact(_("Edit testcase"), afTestcaseNotebook, self.model.saveTestcase, testcase)


    def EditUsecase(self, usecase):
        """
        Edit usecase data in dialog window
        @type  usecase: object
        @param usecase: Usecase object
        @rtype:  nested tuple
        @return: same as L{EditArtefact}
        """
        afconfig.ACTOR_NAME = self.model.requestActorList()
        afconfig.STAKEHOLDER_NAME = self.model.requestStakeholderList()
        self.EditArtefact(_("Edit usecase"), afUsecaseNotebook, self.model.saveUsecase, usecase)


    def EditTestsuite(self, testsuite):
        """
        Edit testsuite data in dialog window
        @type  testsuite: object
        @param testsuite: Testsuite object
        @return: same as L{EditArtefact}
        @rtype:  nested tuple
        """
        self.EditArtefact(_("Edit testsuite"), afTestsuiteNotebook, self.model.saveTestsuite, testsuite)


    def EditSimpleSection(self, simplesection):
        self.EditArtefact(_("Edit section"), afSimpleSectionNotebook, self.model.saveSimpleSection, simplesection)


    def EditGlossaryEntry(self, glossaryentry):
        self.EditArtefact(_("Edit glossary entry"), afGlossaryEntryView, self.model.saveGlossaryEntry, glossaryentry)


    def EditArtefact(self, title, contentview, savedata, data):
        """
        Edit artefact in a dialog window.
        @type        title: string
        @param       title: Dialog window title
        @type  contentview: artefact  view object
        @param contentview: Object to display/edit artefact list
        @type     savedata: function
        @param    savedata: Function to save edited data
        @type         data: nested tuple
        @param        data: Artefact data
        @return: Nested tuple with values
          0. Return value of dialog, either C{wx.SAVE} or C{wx.CANCEL}
          1. Boolean flag indicating a new artefact if set
          2. Possibly edited artefact object
          3. The input parameter contentview
        @rtype:  nested tuple
        """
        logging.debug("afeditor.EditArtefact()")
        dlg = EditArtefactDialog(self.mainframe.rightWindow, -1, title=title, contentview=contentview)
        dlg.contentview.InitContent(data)
        #TODO: pass validator to this function and use this to init validator of contentview
        # this should not be the wxValidator
        dlg.Show()
        dlg.SetFocus() #TODO: testme
        dlg.Bind(wx.EVT_BUTTON, self.EditArtefactDialogSave, id=dlg.savebtn.GetId())
        dlg.Bind(wx.EVT_BUTTON, self.EditArtefactDialogSave, id=dlg.savecontbtn.GetId())
        dlg.Bind(wx.EVT_BUTTON, self.EditArtefactDialogCancel, id=dlg.cancelbtn.GetId())
        self.editparams.editdlg = dlg
        self.editparams.savedata = savedata
        return

    # ----------------------------------------
    def BulkEditFeatures(self):
        afconfig.VERSION_NAME = self.model.requestVersionList('FEATURES')
        aflist = self.model.getFeatureList(affilter=self.featurefilterview.GetFilterContent())
        dlg = _afbulkview.EditBulkArtefactDialog(self.mainframe.rightWindow, _("Edit features"), _afbulkview.afBulkFeatureView, aflist)
        dlg.Bind(wx.EVT_BUTTON, self.BulkEditFeatureDialogSave, id=dlg.savebtn.GetId())
        dlg.Bind(wx.EVT_BUTTON, self.EditArtefactDialogCancel, id=dlg.cancelbtn.GetId())
        self.editparams.editdlg = dlg
        self.editparams.savedata = None
        dlg.Show()


    def BulkEditFeatureDialogSave(self, evt):
        """Called when pressing 'Save' """
        dlg = self.editparams.editdlg
        (artefactids, fields, newtags, changelog) = dlg.contentview.GetContent()
        # fields is dictionary  with keys version, priority, status, risk
        warnid = []
        for id in artefactids:
            af = self.model.getFeature(id)
            af.setTags(newtags)
            af.setChangelog(changelog)
            # current_status    new_status
            # submitted         submitted, approved, completed  allow
            # approved          submitted                       allow
            # approved          approved                        deny any changes
            # approved          completed                       deny any changes except status change
            # completed         submitted                       allow
            # completed         approved                        deny any changes except status change
            # completed         completed                       deny any changes
            if af['status'] == afresource.STATUS_SUBMITTED or fields['status'] == afresource.STATUS_SUBMITTED:
                for key, value in fields.iteritems():
                    if value is not None:
                        af[key] = value
            elif af['status'] == afresource.STATUS_APPROVED or af['status'] == afresource.STATUS_COMPLETED:
                if fields['status'] is not None:
                    af['status'] = fields['status']
                warnid.append(af['ID'])
            else:
                warnid.append(af['ID'])
            self.model.saveFeature(af)
        self.InitFilters()
        self.InitView()
        self.mainframe.treeCtrl.SetSelection(self.editparams.parent_id)
        dlg.Destroy()
        self.__EndEditModal()
        self.BulkEditWarnRejected(warnid)


    def BulkEditRequirements(self):
        afconfig.VERSION_NAME = self.model.requestVersionList('REQUIREMENTS')
        afconfig.ASSIGNED_NAME = self.model.requestAssignedList()
        aflist = self.model.getRequirementList(affilter=self.requirementfilterview.GetFilterContent())
        dlg = _afbulkview.EditBulkArtefactDialog(self.mainframe.rightWindow, _("Edit requirements"), _afbulkview.afBulkRequirementView, aflist)
        dlg.Bind(wx.EVT_BUTTON, self.BulkEditRequirementDialogSave, id=dlg.savebtn.GetId())
        dlg.Bind(wx.EVT_BUTTON, self.EditArtefactDialogCancel, id=dlg.cancelbtn.GetId())
        self.editparams.editdlg = dlg
        self.editparams.savedata = None
        dlg.Show()


    def BulkEditRequirementDialogSave(self, evt):
        """Called when pressing 'Save' """
        dlg = self.editparams.editdlg
        (artefactids, fields, newtags, changelog) = dlg.contentview.GetContent()
        warnid = []
        for id in artefactids:
            af = self.model.getRequirement(id)
            af.setTags(newtags)
            af.setChangelog(changelog)
            if af['status'] == afresource.STATUS_SUBMITTED or fields['status'] == afresource.STATUS_SUBMITTED:
                for key, value in fields.iteritems():
                    if value is not None:
                        af[key] = value
            elif af['status'] == afresource.STATUS_APPROVED or af['status'] == afresource.STATUS_COMPLETED:
                if fields['status'] is not None:
                    af['status'] = fields['status']
                warnid.append(af['ID'])
            else:
                warnid.append(af['ID'])
            self.model.saveRequirement(af)
        self.InitFilters()
        self.InitView()
        self.mainframe.treeCtrl.SetSelection(self.editparams.parent_id)
        dlg.Destroy()
        self.__EndEditModal()
        self.BulkEditWarnRejected(warnid)


    def BulkEditWarnRejected(self, warnid):
        if len(warnid) == 0: return
        msg = _('Some changes may have been rejected for approved or completed artefacts.') + '\n Check ID ' + ', '.join([str(i) for i in warnid])
        wx.MessageDialog(self.mainframe, msg, _('Warning'), wx.ICON_EXCLAMATION|wx.OK).ShowModal()


    def BulkEditUsecases(self):
        afconfig.ACTOR_NAME = self.model.requestActorList()
        afconfig.STAKEHOLDER_NAME = self.model.requestStakeholderList()
        aflist = self.model.getUsecaseList(affilter=self.usecasefilterview.GetFilterContent())
        dlg = _afbulkview.EditBulkArtefactDialog(self.mainframe.rightWindow, _("Edit usecases"), _afbulkview.afBulkUsecaseView, aflist)
        dlg.Bind(wx.EVT_BUTTON, self.BulkEditUsecaseDialogSave, id=dlg.savebtn.GetId())
        dlg.Bind(wx.EVT_BUTTON, self.EditArtefactDialogCancel, id=dlg.cancelbtn.GetId())
        self.editparams.editdlg = dlg
        self.editparams.savedata = None
        dlg.Show()


    def BulkEditUsecaseDialogSave(self, evt):
        """Called when pressing 'Save' """
        dlg = self.editparams.editdlg
        (artefactids, fields, newtags, changelog) = dlg.contentview.GetContent()
        for id in artefactids:
            af = self.model.getUsecase(id)
            af.setTags(newtags)
            af.setChangelog(changelog)
            for key, value in fields.iteritems():
                if value is not None:
                    af[key] = value
            self.model.saveUsecase(af)
        self.InitFilters()
        self.InitView()
        self.mainframe.treeCtrl.SetSelection(self.editparams.parent_id)
        dlg.Destroy()
        self.__EndEditModal()


    def BulkEditTestcases(self):
        afconfig.VERSION_NAME = self.model.requestVersionList('TESTCASES')
        aflist = self.model.getTestcaseList(affilter=self.testcasefilterview.GetFilterContent())
        dlg = _afbulkview.EditBulkArtefactDialog(self.mainframe.rightWindow, _("Edit testcases"), _afbulkview.afBulkTestcaseView, aflist)
        dlg.Bind(wx.EVT_BUTTON, self.BulkEditTestcaseDialogSave, id=dlg.savebtn.GetId())
        dlg.Bind(wx.EVT_BUTTON, self.EditArtefactDialogCancel, id=dlg.cancelbtn.GetId())
        self.editparams.editdlg = dlg
        self.editparams.savedata = None
        dlg.Show()


    def BulkEditTestcaseDialogSave(self, evt):
        """Called when pressing 'Save' """
        dlg = self.editparams.editdlg
        (artefactids, fields, newtags, changelog) = dlg.contentview.GetContent()
        for id in artefactids:
            af = self.model.getTestcase(id)
            af.setTags(newtags)
            af.setChangelog(changelog)
            for key, value in fields.iteritems():
                if value is not None:
                    af[key] = value
            self.model.saveTestcase(af)
        self.InitFilters()
        self.InitView()
        self.mainframe.treeCtrl.SetSelection(self.editparams.parent_id)
        dlg.Destroy()
        self.__EndEditModal()


    def BulkEditSimplesections(self):
        aflist = self.model.getSimpleSectionList(affilter=self.simplesectionfilterview.GetFilterContent())
        dlg = _afbulkview.EditBulkArtefactDialog(self.mainframe.rightWindow, _("Edit text sections"), _afbulkview.afBulkSimplesectionView, aflist)
        dlg.Bind(wx.EVT_BUTTON, self.BulkEditSimplesectionDialogSave, id=dlg.savebtn.GetId())
        dlg.Bind(wx.EVT_BUTTON, self.EditArtefactDialogCancel, id=dlg.cancelbtn.GetId())
        self.editparams.editdlg = dlg
        self.editparams.savedata = None
        dlg.Show()


    def BulkEditSimplesectionDialogSave(self, evt):
        """Called when pressing 'Save' """
        dlg = self.editparams.editdlg
        (artefactids, fields, newtags, changelog) = dlg.contentview.GetContent()
        for id in artefactids:
            af = self.model.getSimpleSection(id)
            af.setTags(newtags)
            af.setChangelog(changelog)
            for key, value in fields.iteritems():
                if value is not None:
                    af[key] = value
            self.model.saveSimpleSection(af)
        self.InitFilters()
        self.InitView()
        self.mainframe.treeCtrl.SetSelection(self.editparams.parent_id)
        dlg.Destroy()
        self.__EndEditModal()


    def BulkEditTestsuites(self):
        aflist = self.model.getTestsuiteList(affilter=self.testsuitefilterview.GetFilterContent())
        dlg = _afbulkview.EditBulkArtefactDialog(self.mainframe.rightWindow, _("Edit testsuites"), _afbulkview.afBulkTestsuiteView, aflist)
        dlg.Bind(wx.EVT_BUTTON, self.BulkEditTestsuiteDialogSave, id=dlg.savebtn.GetId())
        dlg.Bind(wx.EVT_BUTTON, self.EditArtefactDialogCancel, id=dlg.cancelbtn.GetId())
        self.editparams.editdlg = dlg
        self.editparams.savedata = None
        dlg.Show()


    def BulkEditTestsuiteDialogSave(self, evt):
        """Called when pressing 'Save' """
        dlg = self.editparams.editdlg
        (artefactids, fields, newtags, changelog) = dlg.contentview.GetContent()
        for id in artefactids:
            af = self.model.getTestsuite(id)
            af.setTags(newtags)
            af.setChangelog(changelog)
            for key, value in fields.iteritems():
                if value is not None:
                    af[key] = value
            self.model.saveTestsuite(af)
        self.InitFilters()
        self.InitView()
        self.mainframe.treeCtrl.SetSelection(self.editparams.parent_id)
        dlg.Destroy()
        self.__EndEditModal()


    def BulkEditWarnRejected(self, warnid):
        if len(warnid) == 0: return
        msg = _('Some changes may have been rejected for approved or completed artefacts.') + '\n Check ID ' + ', '.join([str(i) for i in warnid])
        wx.MessageDialog(self.mainframe, msg, _('Warning'), wx.ICON_EXCLAMATION|wx.OK).ShowModal()

    # ----------------------------------------

    def requestEditView(self, parent_id, item_id, callback_onsave=Ignore, callback_arg=None):
        """Handle the request to edit an artefact"""
        logging.debug("afeditor.requestEditView(%s, %s) (iseditmode=%d)" % (parent_id, item_id, self.editparams.iseditmode ))
        if self.editparams.iseditmode: return
        self.__BeginEditModal(parent_id, item_id, callback_onsave, callback_arg)

        if item_id == "PRODUCT":
            # Root node of tree is selected, edit project information
            self.EditProductInfo(self.model.getProductInformation())
            self.editparams.iseditmode = False
            self.__EndEditModal()
            return

        elif item_id == None:
            if parent_id == "FEATURES":
                self.BulkEditFeatures()
            elif parent_id == "REQUIREMENTS":
                self.BulkEditRequirements()
            elif parent_id == "USECASES":
                self.BulkEditUsecases()
            elif parent_id == "TESTCASES":
                self.BulkEditTestcases()
            elif parent_id == "TESTSUITES":
                self.BulkEditTestsuites()
            elif parent_id == "SIMPLESECTIONS":
                self.BulkEditSimplesections()
            else:
                self.__EndEditModal()

        elif parent_id == "FEATURES":
            self.EditFeature(self.model.getFeature(item_id))

        elif parent_id == "REQUIREMENTS":
            self.EditRequirement(self.model.getRequirement(item_id))

        elif parent_id == "TESTCASES":
            self.EditTestcase(self.model.getTestcase(item_id))

        elif parent_id == "USECASES":
            self.EditUsecase(self.model.getUsecase(item_id))

        elif parent_id == "TESTSUITES":
            self.EditTestsuite(self.model.getTestsuite(item_id))

        elif parent_id == "SIMPLESECTIONS":
            self.EditSimpleSection(self.model.getSimpleSection(item_id))

        elif parent_id == "GLOSSARYENTRIES":
            self.EditGlossaryEntry(self.model.getGlossaryEntry(item_id))

        return


    def EditArtefactDialogSave(self, evt):
        """Save button pressed in edit artefact dialog"""
        logging.debug("afeditor.EditArtefactDialogSave()")
        dlg = self.editparams.editdlg
        if not dlg.Validate(): return
        continue_edit = evt.GetId() == dlg.savecontbtn.GetId()
        savedata = self.editparams.savedata
        data = dlg.contentview.GetContent()
        try:
            (data, new_artefact) = savedata(data)
            self.editparams.callback_onsave(data, self.editparams.callback_arg)
        except:
            new_artefact = False
            msg = str(sys.exc_info()[0])+"\n"+str(sys.exc_info()[1])
            wx.MessageBox(msg, _('Error saving artefact'), wx.OK | wx.ICON_ERROR)
            logging.error(msg)
            logging.error(sys.exc_info())
        logging.debug("afeditor.EditArtefactDialogSave() done")
        self.InitFilters()
        self.updateView((wx.ID_OK, new_artefact, data, None), self.editparams.parent_id, self.editparams.item_id)
        if continue_edit:
            dlg.contentview.UpdateContent(data)
            self.editparams.item_id = data['ID']
        else:
            dlg.Destroy()
            self.__EndEditModal()


    def EditArtefactDialogCancel(self, evt):
        """Cancel button pressed in edit artefact dialog"""
        logging.debug("afeditor.EditArtefactDialogCancel()")
        dlg = self.editparams.editdlg
        data = None
        new_artefact = False
        dlg.Destroy()
        self.__EndEditModal()


    def __BeginEditModal(self, parent_id, item_id, callback_onsave, callback_arg):
        self.editparams.parent_id = parent_id
        self.editparams.item_id = item_id
        self.editparams.iseditmode = True
        self.mainframe.EnableTools(False)
        self.mainframe.EnableMenus(False)
        self.mainframe.EnableFilters(False)
        self.mainframe.SetStatusText(_('Edit'), 1)
        self.editparams.callback_onsave = callback_onsave
        self.editparams.callback_arg = callback_arg
        if self.editparams.simplesectionlevelbtn is not None: self.editparams.simplesectionlevelbtn.Enable(False)


    def __EndEditModal(self):
        self.editparams.iseditmode = False
        self.mainframe.EnableTools(True)
        self.mainframe.EnableMenus(True)
        self.mainframe.EnableFilters(True)
        self.mainframe.SetStatusText('', 1)
        if self.editparams.simplesectionlevelbtn is not None: self.editparams.simplesectionlevelbtn.Enable(True)


    def undeleteArtefact(self, parent_id, item_id):
        """
        Restore a previously deleted artefact

        @type  parent_id: string
        @param parent_id: The kind of artefact to be restored
        @type    item_id: int
        @param   item_id: The ID of the artefact to restore
        """
        logging.debug("afeditor.undeleteArtefact(parent_id=%s, item_id=%d)" % (parent_id, item_id))
        if not self.dont_annoy_at_undelete:
            (retval, self.dont_annoy_at_undelete) = _afhelper.DontAnnoyMessageBox(_("Really restore artefact?"), _("Restore artefact"))
            if retval == wx.NO: return

        artefact = self.getfuncs[self.PARENTID.index(parent_id)](item_id)
        if artefact.supportsChangelog():
            (retval, changelogentry) = _afhelper.ChangelogEntryMessageBox(_("Enter changelog"))
            if retval != wx.ID_OK: return
        else:
            changelogentry = None

        try:
            data = self.delfuncs[self.PARENTID.index(parent_id)](item_id, delcnt=0, changelogentry=changelogentry)
            self.updateNodeView("TRASH", "TRASH"+parent_id)
            self.mainframe.AddItem(parent_id, data)
            self.mainframe.treeCtrl.UpdateTrashIcons(self.model.getNumberOfDeletedArtefacts())
        except:
            _afhelper.ExceptionMessageBox(sys.exc_info())


    def updateNodeView(self, parent_id, item_id, select_id=0):
        """
        Handle change of selection in the main tree in the left panel

        Depending on the selection in the left tree the display in the right panel
        is updated. This is done by calling one of the methods
            - L{ViewProductInfo}
            - L{ViewArtefactList}
            - L{ViewArtefact}

        @type  parent_id: string
        @param parent_id: String identifying the parent of the selected node
        @type    item_id: integer
        @param   item_id: ID of the selected node
        @type  select_id: integer
        @param select_id: Item to be selected in an artefact list, 0 means none
        """
        if self.DisableUpdateNodeView:
            self.DisableUpdateNodeView = False
            return
        logging.debug("afeditor.updateNodeView(%s, %s)" % (parent_id, item_id))
        self.editparams.simplesectionlevelbtn = None
        if item_id == "PRODUCT":
            # Root node of tree is selected, show project information
            self.ViewProductInfo(self.model.getProductInformation())
            self.mainframe.AddFilterView(self.productfilterview)
            #
        elif item_id == "FEATURES":
            self.ViewArtefactList(afFeatureList, self.featurelistview,
                                  self.model.getFeatureList(affilter=self.featurefilterview.GetFilterContent()),
                                  select_id)
            self.mainframe.AddFilterView(self.featurefilterview)
            #
        elif item_id == "REQUIREMENTS":
            self.ViewArtefactList(afRequirementList, self.requirementlistview,
                                  self.model.getRequirementList(affilter=self.requirementfilterview.GetFilterContent()),
                                  select_id)
            self.mainframe.AddFilterView(self.requirementfilterview)
            #
        elif item_id == "TESTCASES":
            self.ViewArtefactList(afTestcaseList, self.testcaselistview,
                                  self.model.getTestcaseList(affilter=self.testcasefilterview.GetFilterContent()),
                                  select_id)
            self.mainframe.AddFilterView(self.testcasefilterview)
            #
        elif item_id == "TESTSUITES":
            self.ViewArtefactList(afTestsuiteList, self.testsuitelistview,
                                  self.model.getTestsuiteList(affilter=self.testsuitefilterview.GetFilterContent()),
                                  select_id)
            self.mainframe.AddFilterView(self.testsuitefilterview)
            #
        elif item_id == "USECASES":
            self.ViewArtefactList(afUsecaseList, self.usecaselistview,
                                  self.model.getUsecaseList(affilter=self.usecasefilterview.GetFilterContent()),
                                  select_id)
            self.mainframe.AddFilterView(self.usecasefilterview)
            #
        elif item_id == "SIMPLESECTIONS":
            self.ViewArtefactList(afSimpleSectionListWithButton, self.simplesectionlistview,
                                  self.model.getSimpleSectionList(affilter=self.simplesectionfilterview.GetFilterContent()),
                                  select_id)
            self.mainframe.AddFilterView(self.simplesectionfilterview)
            # TODO: enable/disable this button when editing an artefact is not solved elegant
            self.editparams.simplesectionlevelbtn = self.contentview.level_button
            self.contentview.level_button.Enable(not self.editparams.iseditmode)
            #
        elif item_id == "GLOSSARYENTRIES":
            self.ViewArtefactList(afGlossaryEntryList, self.glossaryentrylistview,
                                  self.model.getGlossaryEntryList(affilter=self.glossaryentryfilterview.GetFilterContent()),
                                  select_id)
            self.mainframe.AddFilterView(self.glossaryentryfilterview)
            ##
        elif parent_id == "FEATURES":
            self.ViewArtefact(self.model.getFeature(item_id), afFeatureNotebook, self.featureview)
            self.mainframe.AddFilterView(self.featurefilterview)
        elif parent_id == "REQUIREMENTS":
            self.ViewArtefact(self.model.getRequirement(item_id), afRequirementNotebook, self.requirementview)
            self.mainframe.AddFilterView(self.requirementfilterview)
        elif parent_id == "TESTCASES":
            self.ViewArtefact(self.model.getTestcase(item_id), afTestcaseNotebook, self.testcaseview)
            self.mainframe.AddFilterView(self.testcasefilterview)
        elif parent_id == "USECASES":
            self.ViewArtefact(self.model.getUsecase(item_id), afUsecaseNotebook, self.usecaseview)
            self.mainframe.AddFilterView(self.usecasefilterview)
        elif parent_id == "TESTSUITES":
            self.ViewArtefact(self.model.getTestsuite(item_id), afTestsuiteNotebook, self.testsuiteview)
            self.mainframe.AddFilterView(self.testsuitefilterview)
        elif parent_id == "SIMPLESECTIONS":
            self.ViewArtefact(self.model.getSimpleSection(item_id), afSimpleSectionNotebook, self.simplesectionview)
            self.mainframe.AddFilterView(self.simplesectionfilterview)
        elif parent_id == "GLOSSARYENTRIES":
            self.ViewArtefact(self.model.getGlossaryEntry(item_id), afGlossaryEntryView, self.glossaryentryview)
            self.mainframe.AddFilterView(self.glossaryentryfilterview)
        elif item_id == "TRASHFEATURES":
            self.ViewArtefactList(afFeatureList, self.trashfeaturelistview, self.model.getFeatureList(deleted=True), select_id)
            self.mainframe.AddFilterView(self.nofilterview)
        elif item_id == "TRASHREQUIREMENTS":
            self.ViewArtefactList(afRequirementList, self.trashrequirementlistview, self.model.getRequirementList(deleted=True), select_id)
            self.mainframe.AddFilterView(self.nofilterview)
        elif item_id == "TRASHTESTCASES":
            self.ViewArtefactList(afTestcaseList, self.trashtestcaselistview, self.model.getTestcaseList(deleted=True), select_id)
            self.mainframe.AddFilterView(self.nofilterview)
        elif item_id == "TRASHUSECASES":
            self.ViewArtefactList(afUsecaseList, self.trashusecaselistview, self.model.getUsecaseList(deleted=True), select_id)
            self.mainframe.AddFilterView(self.nofilterview)
        elif item_id == "TRASHTESTSUITES":
            self.ViewArtefactList(afTestsuiteList, self.trashtestsuitelistview, self.model.getTestsuiteList(deleted=True), select_id)
            self.mainframe.AddFilterView(self.nofilterview)
        elif item_id == "TRASHSIMPLESECTIONS":
            self.ViewArtefactList(afSimpleSectionList, self.trashsimplesectionlistview, self.model.getSimpleSectionList(deleted=True), select_id)
            self.mainframe.AddFilterView(self.nofilterview)
        elif item_id == "TRASHGLOSSARYENTRIES":
            self.ViewArtefactList(afGlossaryEntryList, self.trashglossaryentrylistview,
                                  self.model.getGlossaryEntryList(deleted=True),
                                  select_id)
            self.mainframe.AddFilterView(self.nofilterview)
        elif item_id == "TRASH":
            self.ViewTrashInfo(self.model.getNumberOfDeletedArtefacts())
            self.mainframe.AddFilterView(self.nofilterview)


    def updateView(self, editresult, parent_id, item_id):
        """
        Update GUI view after editing an artefact

        This function is called if an artefact has been edited. Following
        actions are performed:
            - The tree in the left panel must be updated
            - If we started editing by activating the artefact in the tree
               we have to update the artefact view in the right panel
            - If we started editing by activating the artefact in a list
              (shown in the right panel), we have to show an updated list

        @type  editresult: nested tuple
        @param editresult: see return value of L{requestEditView}
        @type   parent_id: string
        @param  parent_id: Parent ID of artefact in left tree
        @type     item_id: integer
        @param    item_id: ID of artefact in left tree
        """
        (dlgResult, new_artefact, data, contentview) = editresult
        if dlgResult == wx.ID_CANCEL:
             return
        if new_artefact:
            # Update tree in left panel
            logging.debug("afeditor.updateView() (InitTree)")
            self.mainframe.AddItem(parent_id, data)
            logging.debug("afeditor.updateView() (InitTree done)")
            item_id = data['ID']
        else:
            # Update tree in left panel
            self.mainframe.treeCtrl.UpdateItemText(parent_id, item_id, data)

        self.DisableOnSelChanged = True
        if self.currentview in self.listview:
            # Update artefact list in right panel
            logging.debug("afeditor.updateView() (1)")
            self.updateNodeView(None, parent_id, item_id)
            self.mainframe.treeCtrl.SetSelection(parent_id)
        else:
            # Update artefact view in right panel
            logging.debug("afeditor.updateView() (2)")
            self.updateNodeView(parent_id, item_id)
            self.mainframe.treeCtrl.SetSelection(parent_id, item_id)

        self.DisableOnSelChanged = False


    def getUsername(self):
        "Return the name of the current user"
        return afconfig.CURRENT_USER


    def getCurrentTimeStr(self):
        "Return current date and time as string"
        return time.strftime(afresource.TIME_FORMAT)


    def OnExit(self):
        self.config.Write("workdir", self.model.currentdir)


    def OnImport(self, evt):
        """
        Event handler for menu item 'Import'.
        @type  evt: wx.CommandEvent
        @param evt: event data
        """
        dlg = wx.FileDialog(
            self.mainframe, message = _("Import from product file"),
            defaultDir = self.model.currentdir,
            defaultFile = "",
            wildcard = self.wildcard,
            style=wx.OPEN | wx.FILE_MUST_EXIST
            )
        dlgResult = dlg.ShowModal()
        if  dlgResult == wx.ID_OK:
            path = dlg.GetPath()
        dlg.Destroy()
        if  dlgResult == wx.ID_OK:
            try:
                importer = _afimporter.afImporter(self.mainframe, self.model, path)
                importer.Run()
                self.InitView()
                self.InitFilters()
            except:
                _afhelper.ExceptionMessageBox(sys.exc_info(), _('Error importing artefacts!'))


def main():
    import os, sys, getopt

    global arguments

    def version():
        print("$Rev$")

    def usage():
        print("Editor for Artefact Management System\nUsage:\n%s [-h|--help] [-V|--version] [-d |--debug] [<ifile>]\n"
        "  -h, --help     show help and exit\n"
        "  -V, --version  show version and exit\n"
        "  -d, --debug    enable debug output\n"
        "  <ifile>        database file"
        % sys.argv[0])

    logging.basicConfig(level=afconfig.loglevel, format=afconfig.logformat)
    logging.disable(afconfig.loglevel)

    try:
        opts, arguments = getopt.getopt(sys.argv[1:], "hdV", ["help", "debug", "version"])
    except getopt.GetoptError, err:
        # print help information and exit:
        print str(err) # will print something like "option -a not recognized"
        usage()
        sys.exit(2)

    for o, a in opts:
        if o in ("-V", "--version"):
            version()
            sys.exit()
        elif o in ("-h", "--help"):
            usage()
            sys.exit()
        elif o in ("-d", "--debug"):
            logging.disable(logging.NOTSET)
        else:
            assert False, "unhandled option"

    app = MyApp(redirect=False)
    # Hmmm... If wxLocale is called in app.OnInit() it does not work. Why?
    mylocale = wx.Locale(app.wxLanguageCode)
    app.MainLoop()

if __name__=="__main__":
    main()
