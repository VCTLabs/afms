import pickle
import wx
from afresource import _
import afresource

def copyArtefactToClipboard(dataobj, textobj):
    doc = wx.DataObjectComposite()
    doc.Add(dataobj)
    doc.Add(textobj)
    if wx.TheClipboard.Open():
        wx.TheClipboard.SetData(doc)
    wx.TheClipboard.Close()
    
    
def getArtefactFromClipboard():
    retval = None
    af_data = None
    af_kind = None
    if wx.TheClipboard.Open():
        if wx.TheClipboard.IsSupported(wx.CustomDataFormat('AFMS_FEATURE')):
            af_kind = 'AFMS_FEATURE'
            af_data = afFeatureDataObjectSimple()
        elif wx.TheClipboard.IsSupported(wx.CustomDataFormat('AFMS_REQUIREMENT')):
            af_kind = 'AFMS_REQUIREMENT'
            af_data = afRequirementDataObjectSimple()
        elif wx.TheClipboard.IsSupported(wx.CustomDataFormat('AFMS_USECASE')):
            af_kind = 'AFMS_USECASE'
            af_data = afUsecaseDataObjectSimple()
        elif wx.TheClipboard.IsSupported(wx.CustomDataFormat('AFMS_TESTCASE')):
            af_kind = 'AFMS_TESTCASE'
            af_data = afTestcaseDataObjectSimple()
        elif wx.TheClipboard.IsSupported(wx.CustomDataFormat('AFMS_TESTSUITE')):
            af_kind = 'AFMS_TESTSUITE'
            af_data = afTestsuiteDataObjectSimple()
            
        if af_data is not None:
            if wx.TheClipboard.GetData(af_data):
                retval = pickle.loads(af_data.GetDataHere())
                
        wx.TheClipboard.Close();
        
    return (af_kind, retval)
        
        
class afArtefactDataObjectSimple(wx.PyDataObjectSimple):
    def __init__(self, artefact):
        assert 0==1 # has to be overriden!
        
    def GetDataHere(self):
        return self.data

    def GetDataSize(self):
        return len(self.data)

    def SetData(self, data):
        self.data = data
        return True
    
    
class afArtefactTextObjectSimple(wx.PyDataObjectSimple):
    def __init__(self, afkind, artefact):
        wx.PyDataObjectSimple.__init__(self, wx.DataFormat(wx.DF_TEXT))
        self.data = artefact
        self.afkind = afkind

    def GetDataHere(self):
        return self._formatData()

    def GetDataSize(self):
        return len(self._formatData())
    
    def _formatData(self):
        return "%s: %s" % (str(self.afkind), str(self.data))

    def SetData(self, data):
        self.data = data
        return True
        
# ---------------------------------------------------------------------

def copyFeatureToClipboard(feature):
    af_data = afFeatureDataObjectSimple(pickle.dumps(feature))
    af_text = afFeatureTextObjectSimple('AFMS_FEATURE', feature)
    copyArtefactToClipboard(af_data, af_text)
    
    
class afFeatureDataObjectSimple(afArtefactDataObjectSimple):
    def __init__(self, artefact = None):
        wx.PyDataObjectSimple.__init__(self, wx.CustomDataFormat('AFMS_FEATURE'))
        self.data = artefact


class afFeatureTextObjectSimple(afArtefactTextObjectSimple):
    def _formatData(self):
        s = u""
        labels = [_('ID'), _('Title'), _('Priority'), _('Status'), _('Version'), _('Risk'), _('Description')]
        basedata = list(self.data[0])
        basedata[2] = afresource.PRIORITY_NAME[basedata[2]]
        basedata[3] = afresource.STATUS_NAME[basedata[3]]
        basedata[5] = afresource.RISK_NAME[basedata[5]]
        for label, value in zip(labels, basedata):
            s += u"%s: %s\n" % (label, value)
        return s.encode('iso-8859-1')

# ---------------------------------------------------------------------

def copyRequirementToClipboard(requirement):
    af_data = afRequirementDataObjectSimple(pickle.dumps(requirement))
    af_text = afRequirementTextObjectSimple('AFMS_REQUIREMENT', requirement)
    copyArtefactToClipboard(af_data, af_text)
    
    
class afRequirementDataObjectSimple(afArtefactDataObjectSimple):
    def __init__(self, artefact = None):
        wx.PyDataObjectSimple.__init__(self, wx.CustomDataFormat('AFMS_REQUIREMENT'))
        self.data = artefact


class afRequirementTextObjectSimple(afArtefactTextObjectSimple):
    def _formatData(self):
        s = u""
        labels = [_('ID'), _('Title'), _('Priority'), _('Status'), _('Version'),
                  _('Complexity'), _('Assigned'), _('Effort'), _('Category'),
                  _('Origin'), _('Rationale'), _('Description')]
        basedata = list(self.data[0])
        basedata[2] = afresource.PRIORITY_NAME[basedata[2]]
        basedata[3] = afresource.STATUS_NAME[basedata[3]]
        basedata[5] = afresource.COMPLEXITY_NAME[basedata[5]]
        basedata[7] = afresource.EFFORT_NAME[basedata[7]]
        basedata[8] = afresource.CATEGORY_NAME[basedata[8]]
        for label, value in zip(labels, basedata):
            s += u"%s: %s\n" % (label, value)
        return s.encode('iso-8859-1')

# ---------------------------------------------------------------------

def copyUsecaseToClipboard(usecase):
    af_data = afUsecaseDataObjectSimple(pickle.dumps(usecase))
    af_text = afUsecaseTextObjectSimple('AFMS_USECASE', usecase)
    copyArtefactToClipboard(af_data, af_text)


class afUsecaseDataObjectSimple(afArtefactDataObjectSimple):
    def __init__(self, artefact = None):
        wx.PyDataObjectSimple.__init__(self, wx.CustomDataFormat('AFMS_USECASE'))
        self.data = artefact


class afUsecaseTextObjectSimple(afArtefactTextObjectSimple):
    def _formatData(self):
        s = u""
        labels = [_('ID'), _('Summary'), _('Priority'), _('Use frequency'),
                  _('Actors'), _('Stakeholders'), _('Prerequisites'),
                  _('Main scenario'), _('Alt scenario'), _('Notes')]
        basedata = list(self.data[0])
        basedata[2] = afresource.PRIORITY_NAME[basedata[2]]
        basedata[3] = afresource.USEFREQUENCY_NAME[basedata[3]]
        for label, value in zip(labels, basedata):
            s += u"%s: %s\n" % (label, value)
        return s.encode('iso-8859-1')

# ---------------------------------------------------------------------

def copyTestcaseToClipboard(testcase):
    af_data = afTestcaseDataObjectSimple(pickle.dumps(testcase))
    af_text = afTestcaseTextObjectSimple('AFMS_TESTCASE', testcase)
    copyArtefactToClipboard(af_data, af_text)


class afTestcaseDataObjectSimple(afArtefactDataObjectSimple):
    def __init__(self, artefact = None):
        wx.PyDataObjectSimple.__init__(self, wx.CustomDataFormat('AFMS_TESTCASE'))
        self.data = artefact


class afTestcaseTextObjectSimple(afArtefactTextObjectSimple):
        def _formatData(self):
            s = u""
            labels = [_('ID'), _('Title'), _('Purpose'),
                      _('Prerequisite'), _('Testdata'), _('Steps'),
                      _('Notes && Questions'), _('Version')]
            basedata = list(self.data[0])
            for label, value in zip(labels, basedata):
                s += u"%s: %s\n" % (label, value)
            return s.encode('iso-8859-1')

# ---------------------------------------------------------------------

def copyTestsuiteToClipboard(testsuite):
    af_data = afTestsuiteDataObjectSimple(pickle.dumps(testsuite))
    af_text = afTestsuiteTextObjectSimple('AFMS_TESTSUITE', testsuite)
    copyArtefactToClipboard(af_data, af_text)


class afTestsuiteDataObjectSimple(afArtefactDataObjectSimple):
    def __init__(self, artefact = None):
        wx.PyDataObjectSimple.__init__(self, wx.CustomDataFormat('AFMS_TESTSUITE'))
        self.data = artefact


class afTestsuiteTextObjectSimple(afArtefactTextObjectSimple):
    def _formatData(self):
        s = u""
        labels = [_("ID"), _("Title"), _("Description"), _("Execution order ID's")]
        basedata = list(self.data[0])
        for label, value in zip(labels, basedata):
            s += u"%s: %s\n" % (label, value)
        return s.encode('iso-8859-1')

