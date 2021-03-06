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

# $Id$

import sys
import logging
import wx
import  wx.lib.mixins.listctrl  as  listmix
from wx.lib.mixins.listctrl  import CheckListCtrlMixin
import _afimages, _afhelper
import afconfig
import afresource
from _afsimplesectionleveldialog import EditSimpleSectionLevelDialog


class CheckTristateListCtrlMixin(CheckListCtrlMixin):
    def __init__(self, check_image=None, uncheck_image=None):
        CheckListCtrlMixin.__init__(self, check_image, uncheck_image)
        self.__CreateBitmap = self._CheckListCtrlMixin__CreateBitmap
        self.__imagelist_ = self._CheckListCtrlMixin__imagelist_
        tristate_image = self.__CreateBitmap(wx.CONTROL_UNDETERMINED)
        self.tristate_image = self.__imagelist_.Add(tristate_image)


    def TristateItem(self, index):
        self.SetItemImage(index, 2)


    def CheckItem(self, index, check = True):
        img_idx = self.GetItem(index).GetImage()
        if img_idx in (1, 2) and check is False:
            self.SetItemImage(index, 0)
            self.OnCheckItem(index, False)
        elif img_idx in (0, 2) and check is True:
            self.SetItemImage(index, 1)
            self.OnCheckItem(index, True)


    def GetState(self, index):
        return self.GetItem(index).GetImage()


class ArtefactListCtrl(wx.ListCtrl, listmix.ListCtrlAutoWidthMixin, CheckTristateListCtrlMixin):
    def __init__(self, parent, ID, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0, checkstyle=False):
        wx.ListCtrl.__init__(self, parent, ID, pos, size, style)
        listmix.ListCtrlAutoWidthMixin.__init__(self)
        self.parent = parent
        if checkstyle:
            CheckTristateListCtrlMixin.__init__(self)


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
                    #style=wx.LC_SORT_ASCENDING | wx.LC_REPORT | wx.BORDER_NONE | wx.LC_VRULES | wx.LC_HRULES | wx.LC_SINGLE_SEL,
                    style=wx.LC_REPORT | wx.BORDER_NONE | wx.LC_VRULES | wx.LC_HRULES | wx.LC_SINGLE_SEL,
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


    def FormatRow(self, afobj):
        assert(0==1) # aka virtual function


    def ColorsForRow(self, afobj):
        return _afhelper.getColorForArtefact(afobj)[0]


    def InitContent(self, artefact_list, select_id=0):
        self.itemDataMap = {}
        self.artefactlist = artefact_list
        for i in range(len(artefact_list)):
            ID = artefact_list[i]['ID']
            data = self.FormatRow(artefact_list[i])
            color = self.ColorsForRow(artefact_list[i])
            self.itemDataMap[i] = data
            if self.checkstyle:
                index = self.list.InsertStringItem(sys.maxint, data[0])
            else:
                index = self.list.InsertStringItem(sys.maxint, data[0])
                #index = self.list.InsertImageStringItem(sys.maxint, "%04d" % data[0], self.empty)
            self.list.SetItemData(index, i)
            self.list.SetItemTextColour(index, color)

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
            # show all contents
            self.InitContent(checkedcontent+uncheckedcontent)
            # check all checkedcontent
            for i in range(len(checkedcontent)):
                self.list.CheckItem(i)
        else:
            self.InitContent(checkedcontent)


    def InitTristateContent(self, tristatecontent):
        for i in range(len(tristatecontent)):
            self.list.TristateItem(i)


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
        ID = item['ID']
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


    def ChangeItem(self, index, newitem):
        data = self.FormatRow(newitem)
        i = self.list.GetItemData(index)
        self.itemDataMap[i] = data
        for j in range(self.num_of_columns):
            if isinstance(data[j], (type(''), type(u''))):
                self.list.SetStringItem(index, j, data[j])
            else:
                self.list.SetStringItem(index, j, str(data[j]))


    def toText(self, s):
        """Make s printable in one line"""
        s = s.strip()
        if len(s) > 150:
            s = s[:147] + '...'
        if s.upper().startswith(".. REST"):
            s = s[7:]
        elif s.upper().startswith("<HTML>"):
            s = s[6:]
        elif s.upper().startswith(".. HTML"):
            s = s[7:]
        s = s.strip()
        # Replace multiple newlines by a single '|' char
        s = '|'.join([part for part in s.split('\n') if len(part) > 0])
        # Replace multiple tabs by a single blank char
        s = ' '.join([part for part in s.split('\t') if len(part) > 0])
        return s


    def GetChangeDate(self, obj):
        try:
            return obj.getChangelist()[0]['date']
        except IndexError:
            return ''


    def GetChangeUser(self, obj):
        try:
            return obj.getChangelist()[0]['user']
        except IndexError:
            return ''

#-------------------------------------------------------------------------

class afFeatureList(afArtefactList):
    """Widget for displaying feature lists"""
    def __init__(self, parent, ID = -1, checkstyle=False):
        # Column titles of the feature list table
        self.column_titles = [_('ID'), _('Title'), _('Priority'), _('Status'),
            _('Version'), _('Risk'), _('Date'), _('User'), _('Description')]
        self.key = "FEATURES"
        afArtefactList.__init__(self, parent, self.column_titles, ID, checkstyle)

    def FormatRow(self, ftobj):
        try:
            changedata = ftobj.getChangelist()[0]
        except IndexError:
            changedata = {'date' : '', 'user': ''}

        return (self.idformat % ftobj['ID'],
                ftobj['title'],
                _(afresource.PRIORITY_NAME[ftobj['priority']]),
                _(afresource.STATUS_NAME[ftobj['status']]),
                ftobj['version'],
                _(afresource.RISK_NAME[ftobj['risk']]),
                self.GetChangeDate(ftobj),
                self.GetChangeUser(ftobj),
                self.toText(ftobj['description']))

#-------------------------------------------------------------------------

class afRequirementList(afArtefactList):
    """Widget for displaying requirements lists"""
    def __init__(self, parent, ID = -1, checkstyle=False):
        self.column_titles = [_('ID'), _('Title'), _('Priority'), _('Status'),
            _('Complexity'), _('Assigned'), _('Effort'), _('Category'), _('Version'),
            _('Date'), _('User'), _('Description')]
        self.key = "REQUIREMENTS"
        afArtefactList.__init__(self, parent, self.column_titles, ID, checkstyle=checkstyle)

    def FormatRow(self, rqobj):
        return (self.idformat % rqobj['ID'],
                rqobj['title'],
                _(afresource.PRIORITY_NAME[rqobj['priority']]),
                _(afresource.STATUS_NAME[rqobj['status']]),
                _(afresource.COMPLEXITY_NAME[rqobj['complexity']]),
                rqobj['assigned'],
                _(afresource.EFFORT_NAME[rqobj['effort']]),
                _(afresource.CATEGORY_NAME[rqobj['category']]),
                rqobj['version'],
                self.GetChangeDate(rqobj),
                self.GetChangeUser(rqobj),
                self.toText(rqobj['description']))

#-------------------------------------------------------------------------

class afTestcaseList(afArtefactList):
    """Widget for displaying testcase lists"""
    def __init__(self, parent, ID = -1, checkstyle=False):
        self.column_titles = [_('ID'), _('Title'), _('Version'), _('Date'), _('User'), _('Script URL'), _('Purpose')]
        self.key = "TESTCASES"
        afArtefactList.__init__(self, parent, self.column_titles, ID, checkstyle=checkstyle)


    def FormatRow(self, tcobj):
        return (self.idformat % tcobj['ID'],
                tcobj['title'],
                tcobj['version'],
                self.GetChangeDate(tcobj),
                self.GetChangeUser(tcobj),
                self.toText(tcobj['scripturl']),
                self.toText(tcobj['purpose']))

#-------------------------------------------------------------------------

class afUsecaseList(afArtefactList):
    """Widget for displaying usecase lists"""
    def __init__(self, parent, ID = -1, checkstyle=False):
        self.column_titles = [_('ID'), _('Summary'), _('Priority'), _('Use freq.'), _('Actors'), _('Stakeholders'), _('Date'), _('User')]
        self.key = "USECASES"
        afArtefactList.__init__(self, parent, self.column_titles, ID, checkstyle=checkstyle)


    def FormatRow(self, ucobj):
        return (self.idformat % ucobj['ID'],
                ucobj['title'],
                _(afresource.PRIORITY_NAME[ucobj['priority']]),
                _(afresource.USEFREQUENCY_NAME[ucobj['usefrequency']]),
                ucobj['actors'],
                ucobj['stakeholders'],
                self.GetChangeDate(ucobj),
                self.GetChangeUser(ucobj))

#-------------------------------------------------------------------------

class afTestsuiteList(afArtefactList):
    """Widget for displaying testsuites lists"""
    def __init__(self, parent, ID = -1, checkstyle=False):
        self.column_titles = [_('ID'), _('Title'), '# '+_('Testcases'), _('Description')]
        self.key = "TESTSUITES"
        afArtefactList.__init__(self, parent, self.column_titles, ID, checkstyle=checkstyle)


    def FormatRow(self, tsobj):
        return (self.idformat % tsobj['ID'],
                tsobj['title'],
                tsobj['nbroftestcase'],
                self.toText(tsobj['description']))

#-------------------------------------------------------------------------

class afSimpleSectionList(afArtefactList):
    """Widget for displaying simplesection lists"""
    def __init__(self, parent, ID = -1, checkstyle=False):
        self.column_titles = [_('ID'), _('Level'), _('Title')]
        self.key = "SIMPLESECTIONS"
        afArtefactList.__init__(self, parent, self.column_titles, ID, checkstyle=checkstyle)


    def FormatRow(self, ssobj):
        return (self.idformat % ssobj['ID'],
                ssobj['level'],
                ssobj['title'])

#-------------------------------------------------------------------------

class afSimpleSectionListWithButton(afSimpleSectionList):
    """Widget for displaying simplesection lists with button to edit order"""
    def __init__(self, parent, ID = -1, checkstyle=False):
        afSimpleSectionList.__init__(self, parent, ID, checkstyle=checkstyle)

        self.level_button = wx.Button(self, 5137, _("Edit order") + " ...")
        self.Bind(wx.EVT_BUTTON, self.OnLevelButtonClick, self.level_button)
        self.GetSizer().Add(self.level_button, 0, wx.ALIGN_LEFT)


    def OnLevelButtonClick(self, evt):
        items = ['%(ID)d: %(title)s' % simplesection for simplesection in self.artefactlist]
        dlg = EditSimpleSectionLevelDialog(items)
        dlgResult = dlg.ShowModal()
        if  dlgResult == wx.ID_OK:
            items = dlg.GetItems()
        dlg.Destroy()
        if  dlgResult != wx.ID_OK: return

        ID = [int(s.split(':', 1)[0]) for s in items]
        evt.SetClientData(ID)
        evt.Skip()

#-------------------------------------------------------------------------

class afGlossaryEntryList(afArtefactList):
    """Widget for displaying glossaryentry lists"""
    def __init__(self, parent, ID = -1, checkstyle=False):
        self.column_titles = [_('ID'), _('Term'), _('Description')]
        self.key = "GLOSSARYENTRIES"
        afArtefactList.__init__(self, parent, self.column_titles, ID, checkstyle=checkstyle)


    def FormatRow(self, geobj):
        return (self.idformat % geobj['ID'],
                geobj['title'],
                self.toText(geobj['description']))

#-------------------------------------------------------------------------

class afGlossaryEntryListWithButton(afGlossaryEntryList):
    """Widget for displaying glossaryentry lists with add button"""
    def __init__(self, parent, ID = -1, checkstyle=False):
        afGlossaryEntryList.__init__(self, parent, ID, checkstyle=checkstyle)
        self.add_button = wx.Button(self, 307, _("Add") + " ...")
        self.GetSizer().Add(self.add_button, 0, wx.ALIGN_LEFT)

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
        """Return formated strings for one row in the change list.
        If description string is empty, display a description according to the changetype."""
        description = row['description']
        if len(description) <= 0:
            description = _(afresource.CHANGETYPE_NAME[row['changetype']])
        return (row['user'], row['date'], self.toText(description), row['changetype'])


    def OnItemSelected(self, event):
        self.currentItem = event.m_itemIndex
        self.longdescription.SetValue(self.list.GetItem(self.currentItem, 2).GetText())

#-------------------------------------------------------------------------

class afTagList(afArtefactList):
    """Widget for displaying tag lists"""
    def __init__(self, parent, ID = -1, checkstyle=False):
        self.column_titles = [_('ID'), _('Short description'), _('Description')]
        self.key = "TAGS"
        afArtefactList.__init__(self, parent, self.column_titles, ID, checkstyle=checkstyle)


    def FormatRow(self, tagobj):
        return (self.idformat % tagobj['ID'],
                tagobj['shortdesc'],
                self.toText(tagobj['longdesc']))


    def ColorsForRow(self, tagobj):
        return tagobj.color[tagobj['color']]