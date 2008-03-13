# -*- coding: latin-1  -*-

# -------------------------------------------------------------------
# Copyright 2008 Achim K�hler
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

import sys
import wx
import  wx.lib.mixins.listctrl  as  listmix
import _afimages
import afconfig
from afresource import _
import afresource
import logging

class ArtefactListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin, listmix.CheckListCtrlMixin):
    def __init__(self, parent, ID, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0, checkstyle=False):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)
        self.parent = parent
        if checkstyle:
            listmix.CheckListCtrlMixin.__init__(self)


    def OnCheckItem(self, index, flag):
        evt = wx.CommandEvent(wx.EVT_CHECKLISTBOX.evtType[0], self.GetId())
        evt.SetClientData((self.parent, index, flag))
        self.Command(evt)


class afArtefactList(wx.Panel, listmix.ColumnSorterMixin):
    def __init__(self, parent, column_titles, ID = -1, checkstyle=False):
        wx.Panel.__init__(self, parent, ID, style=wx.WANTS_CHARS)

        self.idformat = "%4d"
        self.checkstyle = checkstyle
        tID = wx.NewId()
        
        # TODO: sorting of numeric columns has to be fixed
        self.list = ArtefactListCtrl(self, tID, size=parent.GetSize(),
                    style=wx.LC_SORT_ASCENDING | wx.LC_REPORT | wx.BORDER_NONE | wx.LC_VRULES | wx.LC_HRULES | wx.LC_SINGLE_SEL,
                    checkstyle=checkstyle)

        # we already have an image list when we are using listmix.CheckListCtrlMixin
        self.il = self.list.GetImageList(wx.IMAGE_LIST_SMALL)
        if self.il is None:
            self.il = wx.ImageList(16, 16)
            self.list.SetImageList(self.il, wx.IMAGE_LIST_SMALL)
        self.empty = self.il.Add(_afimages.getEmptyBitmap())
        self.sm_up = self.il.Add(_afimages.getSmallUpArrowBitmap())
        self.sm_dn = self.il.Add(_afimages.getSmallDnArrowBitmap())

        self.num_of_columns = len(column_titles)

        for i in range(self.num_of_columns):
            self.list.InsertColumn(i, column_titles[i])

        # Now that the list exists we can init the other base class,
        # see wx/lib/mixins/listctrl.py
        listmix.ColumnSorterMixin.__init__(self, self.num_of_columns)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.list, 2, wx.EXPAND | wx.ALL)
        self.SetSizer(sizer)
        self.SetAutoLayout(True)

        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated, self.list)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, self.list)
        if self.checkstyle:
            self.list.Bind(wx.EVT_CHAR, self.OnKeyChar)
            self.Bind(wx.EVT_CHECKLISTBOX, self.OnListItemChecked)
        self.currentItem = None

    def FormatRow(self, row):
        r = list(row)
        try:
            r[0] = self.idformat % row[0]
        except:
            pass
        return tuple(r)
    
    
    def InitContent(self, artefact_list, select_id=0):
        self.itemDataMap = {}
        for i in range(len(artefact_list)):
            ID = artefact_list[i][0]
            data = self.FormatRow(artefact_list[i])
            self.itemDataMap[i] = data
            if self.checkstyle:
                index = self.list.InsertStringItem(sys.maxint, data[0])
            else:
                index = self.list.InsertStringItem(sys.maxint, data[0])
                #index = self.list.InsertImageStringItem(sys.maxint, "%04d" % data[0], self.empty)
            self.list.SetItemData(index, i)
            
            for j in range(self.num_of_columns):
                if isinstance(data[j], (type(''), type(u''))):
                    self.list.SetStringItem(index, j, data[j])
                else:
                    self.list.SetStringItem(index, j, str(data[j]))

            if ID == select_id:
                self.list.SetItemState(index, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED , wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED )

        for i in range(self.num_of_columns):
            self.list.SetColumnWidth(i, wx.LIST_AUTOSIZE)
            
        self.list.SetColumnWidth(0, wx.LIST_AUTOSIZE_USEHEADER)
        self.list.SetColumnWidth(0, self.list.GetColumnWidth(0)+20)
        
        
    def InitCheckableContent(self, uncheckedcontent, checkedcontent, showonlychecked=False):
        if not showonlychecked:
            # disable sorting
            self.list.SetSingleStyle(wx.LC_SORT_ASCENDING, False)
            self.list.SetSingleStyle(wx.LC_SORT_DESCENDING, False)
            # show all contents
            self.InitContent(checkedcontent+uncheckedcontent)
            # check all checkedcontent
            # for this to work we have disabled sorting
            for i in range(len(checkedcontent)):
                self.list.CheckItem(i)
        else:
            self.InitContent(checkedcontent)


    def GetItemIDByCheckState(self):
        checkedID = []
        uncheckedID = []
        for i in range(self.list.GetItemCount()):
            ID = int(self.itemDataMap[i][0])
            if self.list.IsChecked(i):
                checkedID.append(ID)
            else:
                uncheckedID.append(ID)
        return (checkedID, uncheckedID)

    # Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
    def GetListCtrl(self):
        return self.list


    # Used by the ColumnSorterMixin, see wx/lib/mixins/listctrl.py
    def GetSortImages(self):
        return (self.sm_dn, self.sm_up)
    
    
    def OnKeyChar(self, event):
        """
        A key is pressed for the artefact list
        Ctrl-A        selects all list items
        Shift-Ctrl-A  deselects all list items
        Space         Toggles the current selection
        Ctrl-Space    Toggles all selections
        """
        keycode = event.GetKeyCode()
        modifiers = event.GetModifiers()
        if (keycode == 1) and (modifiers & wx.MOD_CONTROL != 0):
            # Ctrl-A is pressed
            logging.debug("afArtefactList.OnKeyChar() ==> Ctrl-A")
            for i in range(self.list.GetItemCount()):
            # Select all items on Ctrl-A, deselect all items on Shift-Ctrl-A
                state = modifiers & wx.MOD_SHIFT == 0
                self.list.CheckItem(i, state)
        elif (keycode == 32) and (modifiers & wx.MOD_CONTROL != 0):
            # Ctrl-Space toggles all selections
            logging.debug("afArtefactList.OnKeyChar() ==> Ctrl-Space")
            for i in range(self.list.GetItemCount()):
                state = not self.list.IsChecked(i)
                self.list.CheckItem(i, state)
        event.Skip()
        
        
    def OnItemActivated(self, event):
        self.currentItem = event.m_itemIndex
        if self.checkstyle:
            self.list.ToggleItem(event.m_itemIndex)
        event.Skip()


    def OnListItemChecked(self, evt):
        """Event handler called when list item is checked/unchecked
           Client data returns tuple with list object, list index and check state
        """
        self.currentItem = evt.GetClientData()[1]
        evt.Skip()
        

    def OnItemSelected(self, event):
        self.currentItem = event.m_itemIndex
        

    def GetSelectionID(self):
        if self.currentItem is None:
            return ((self.key, None))
        else:
            return (self.key, int(self.list.GetItemText(self.currentItem)))
    
    
    def DeleteSelectedItem(self):
        self.list.DeleteItem(self.currentItem)
        self.list.SetItemState(self.currentItem, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED , wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED )


    def CheckItems(self, idlist, check=True):
        """Check/uncheck all items specified by the ID in idlist"""
        for i in range(self.list.GetItemCount()):
            ID = int(self.itemDataMap[i][0])
            if ID in idlist:
                self.list.CheckItem(i, True)
                
                
    def AppendItem(self, item):
        ID = item[0]
        data = self.FormatRow(item)
        i = len(self.itemDataMap)
        self.itemDataMap[i] = data
        index = self.list.InsertStringItem(sys.maxint, data[0])
        self.list.SetItemData(index, i)

        for j in range(self.num_of_columns):
            if isinstance(data[j], (type(''), type(u''))):
                self.list.SetStringItem(index, j, data[j])
            else:
                self.list.SetStringItem(index, j, str(data[j]))
        
#-------------------------------------------------------------------------

class afFeatureList(afArtefactList):
    """Widget for displaying feature lists"""
    ## Class constructor
    ## @param parent The parent window of this widget
    def __init__(self, parent, ID = -1, checkstyle=False):
        ## Column titles of the feature list table
        self.column_titles = [_('ID'), _('Title'), _('Priority'), _('Status'), _('Version'), _('Risk'), _('Description')]
        self.key = "FEATURES"
        afArtefactList.__init__(self, parent, self.column_titles, ID, checkstyle)
        
    def FormatRow(self, row):
        r = list(row)
        try:
            r[0] = self.idformat % row[0]
            r[2] = afresource.PRIORITY_NAME[row[2]]
            r[3] = afresource.STATUS_NAME[row[3]]
            r[5] = afresource.RISK_NAME[row[5]]
        except:
            pass
        return tuple(r)

#-------------------------------------------------------------------------

class afRequirementList(afArtefactList):
    """Widget for displaying requirements lists"""
    def __init__(self, parent, ID = -1, checkstyle=False):
        self.column_titles = [_('ID'), _('Title'), _('Priority'), _('Status'),
            _('Complexity'), _('Assigned'), _('Effort'), _('Category'), _('Version'), _('Description')]
        self.key = "REQUIREMENTS"
        afArtefactList.__init__(self, parent, self.column_titles, ID, checkstyle=checkstyle)
        
    def FormatRow(self, row):
        r = list(row)
        try:
            r[0] = self.idformat % row[0]
            r[2] = afresource.PRIORITY_NAME[row[2]]
            r[3] = afresource.STATUS_NAME[row[3]]
            r[4] = afresource.COMPLEXITY_NAME[row[4]]
            r[6] = afresource.EFFORT_NAME[row[6]]
            r[7] = afresource.CATEGORY_NAME[row[7]]
        except:
            print "Oops"
            pass
        return tuple(r)

#-------------------------------------------------------------------------

class afTestcaseList(afArtefactList):
    """Widget for displaying testcase lists"""
    def __init__(self, parent, ID = -1, checkstyle=False):
        self.column_titles = [_('ID'), _('Title'), _('Version'), _('Purpose')]
        self.key = "TESTCASES"
        afArtefactList.__init__(self, parent, self.column_titles, ID, checkstyle=checkstyle)

#-------------------------------------------------------------------------

class afUsecaseList(afArtefactList):
    """Widget for displaying usecase lists"""
    # ID summary priority usefrequency actors stakeholders prerequisites mainscenario altscenario notes
    def __init__(self, parent, ID = -1, checkstyle=False):
        self.column_titles = [_('ID'), _('Summary'), _('Priority'), _('Use freq.'), _('Actors'), _('Stakeholders')]
        self.key = "USECASES"
        afArtefactList.__init__(self, parent, self.column_titles, ID, checkstyle=checkstyle)

    def FormatRow(self, row):
        r = list(row)
        try:
            r[0] = self.idformat % row[0]
            r[2] = afresource.PRIORITY_NAME[row[2]]
            r[3] = afresource.USEFREQUENCY_NAME[row[3]]
        except:
            pass
        return tuple(r)

#-------------------------------------------------------------------------

class afTestsuiteList(afArtefactList):
    """Widget for displaying testsuites lists"""
    def __init__(self, parent, ID = -1, checkstyle=False):
        self.column_titles = [_('ID'), _('Title'), '# '+_('Testcases'), _('Description')]
        self.key = "TESTSUITES"
        afArtefactList.__init__(self, parent, self.column_titles, ID, checkstyle=checkstyle)

#-------------------------------------------------------------------------

class afChangeList(afArtefactList):
    """Widget for displaying change lists"""
    def __init__(self, parent, ID = -1, checkstyle=False):
        self.column_titles = [_('User'), _('Date'), _('Description')]
        self.key = "CHANGELOG"
        afArtefactList.__init__(self, parent, self.column_titles, ID, checkstyle=checkstyle)
        sizer = self.GetSizer()
        label = wx.StaticText(self, -1, self.column_titles[2]+':')
        self.longdescription = wx.TextCtrl(self, -1, "", style=wx.TE_MULTILINE|wx.TE_READONLY)
        sizer.Add(label, 0, wx.EXPAND | wx.TOP|wx.BOTTOM, 5)
        sizer.Add(self.longdescription, 1, wx.EXPAND)
        self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, self.list)
        
        
    def FormatRow(self, row):
        "If description string is empty, display a description according to the changetype"
        r = list(row)
        description = r[2]
        changetype = r[3]
        if len(description) <= 0:
            description = afresource.CHANGETYPE_NAME[changetype]
            r[2] = description
        return tuple(r)


    def OnItemSelected(self, event):
        self.currentItem = event.m_itemIndex
        self.longdescription.SetValue(self.list.GetItem(self.currentItem, 2).GetText())
