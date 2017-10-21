#!/usr/bin/env python
#
# widgets_list.py - A widget for editing a List property.
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#
"""A widget for editing a :class:`.List` property.

.. warning:: The code in this module is old, and probably doesn't work. It
             will be  updated when I, or somebody else,  needs a list widget.
"""

import wx

import fsleyes_widgets.elistbox as elistbox
from . import properties_types  as ptypes
from . import                      widgets


def _pasteDataDialog(parent, hasProps, propObj):
    """Displays a dialog containing an editable text field, allowing the
    user to type/paste bulk data which will be used to populate the list
    (one line per item).

    :param parent:   parent GUI object

    :param hasProps: The :class:`.HasProperties` object which owns the
                     ``propObj``.

    :param propObj:  The :class:`.List` property object.
    """

    listObj  = getattr(hasProps, propObj.getLabel(hasProps))
    initText = '\n'.join([str(l).strip() for l in listObj])

    frame = wx.Dialog(parent,
                      style=wx.DEFAULT_DIALOG_STYLE |
                            wx.RESIZE_BORDER)
    panel = wx.Panel(frame)
    text  = wx.TextCtrl(panel, value=initText,
                        style=wx.TE_MULTILINE |
                              wx.TE_DONTWRAP  |
                              wx.VSCROLL      |
                              wx.HSCROLL)

    # ok/cancel buttons
    okButton     = wx.Button(panel, label="Ok")
    cancelButton = wx.Button(panel, label="Cancel")

    sizer = wx.GridBagSizer()

    panel.SetSizer(sizer)

    sizer.Add(text,         pos=(0, 0), span=(1, 2), flag=wx.EXPAND)
    sizer.Add(okButton,     pos=(1, 0), span=(1, 1), flag=wx.EXPAND)
    sizer.Add(cancelButton, pos=(1, 1), span=(1, 1), flag=wx.EXPAND)

    sizer.AddGrowableRow(0)
    sizer.AddGrowableCol(0)
    sizer.AddGrowableCol(1)

    def pasteIntoList():
        """
        Called when the user pushes 'Ok'. Copies whatever the
        user typed/pasted into the text area into the list, and
        closes the dialog window.
        """

        listData = text.GetValue().strip()
        listData = listData.split('\n')
        listData = [s.strip() for s in listData]

        setattr(hasProps, propObj.getLabel(hasProps), listData)
        frame.Close()

    okButton    .Bind(wx.EVT_BUTTON, lambda e: pasteIntoList())
    cancelButton.Bind(wx.EVT_BUTTON, lambda e: frame.Close())

    panel.Fit()
    panel.Layout()

    frame.ShowModal()


def _editListDialog(parent, hasProps, propObj):
    """A dialog which displays a widget for every item in the list, and
    which allows the user to adjust the number of items in the list.

    See the :func:`_pasteDataDialog` for details on the parameters.
    """

    # listObj is a properties_values.PropertyValueList object
    listObj  = getattr(hasProps, propObj.getLabel(hasProps))
    listType = propObj._listType
    propName = propObj.getLabel(hasProps)

    # min/max values for a spin box which allows the
    # user to select the number of items in the list
    minval = propObj.getAttribute(hasProps, 'minlen')
    maxval = propObj.getAttribute(hasProps, 'maxlen')

    if minval is None: minval = 0
    if maxval is None: maxval = 2 ** 31 - 1

    frame        = wx.Dialog(parent,
                             style=wx.DEFAULT_DIALOG_STYLE |
                                   wx.RESIZE_BORDER)
    numRowsPanel = wx.Panel(frame)
    entryPanel   = wx.ScrolledWindow(frame)
    okButton     = wx.Button(frame, label='Ok')

    # Spin box (and label) to adjust the
    # number of entries in the list
    numRowsSizer = wx.BoxSizer(wx.HORIZONTAL)
    numRowsPanel.SetSizer(numRowsSizer)

    numRowsLabel = wx.StaticText(numRowsPanel, label='Number of entries')
    numRowsCtrl  = wx.SpinCtrl(numRowsPanel,
                               min=minval,
                               max=maxval,
                               initial=len(listObj))

    numRowsSizer.Add(numRowsLabel, flag=wx.EXPAND, proportion=1)
    numRowsSizer.Add(numRowsCtrl,  flag=wx.EXPAND, proportion=1)

    listWidgets = []

    # Make a widget for every element in the list
    propVals = listObj.getPropertyValueList()
    for propVal in propVals:
        widget  = widgets.makeWidget(entryPanel, hasProps, propName)
        listWidgets.append(widget)

    frameSizer = wx.BoxSizer(wx.VERTICAL)
    frame.SetSizer(frameSizer)
    frameSizer.Add(numRowsPanel, flag=wx.EXPAND)
    frameSizer.Add(entryPanel,   flag=wx.EXPAND, proportion=1)
    frameSizer.Add(okButton,     flag=wx.EXPAND)

    entryPanelSizer = wx.BoxSizer(wx.VERTICAL)
    entryPanel.SetSizer(entryPanelSizer)
    for lw in listWidgets:
        entryPanelSizer.Add(lw, flag=wx.EXPAND)


    def changeNumRows(*args):
        """
        Called when the numRows variable is changed (via the numRows
        spinbox). Adds or removes the last  item from the property
        list, and corresponding widget from the window.
        """

        oldLen   = len(listObj)
        newLen   = numRowsCtrl.GetValue()

        # add rows
        default = listType.getAttribute(hasProps, 'default')
        while oldLen < newLen:

            # add a new element to the list
            listObj.append(default)

            # add a widget
            widg = widgets.makeWidget(entryPanel, hasProps, propName)
            listWidgets.append(widg)
            entryPanelSizer.Add(widg, flag=wx.EXPAND)

            oldLen = oldLen + 1

        # remove rows
        while oldLen > newLen:

            # kill the list item
            listObj.pop()

            # kill the widget
            widg = listWidgets.pop()

            entryPanelSizer.Remove(widg)

            widg.Destroy()

            oldLen = oldLen - 1
        entryPanel.Layout()
        entryPanel.Refresh()


    numRowsCtrl.Bind(wx.EVT_SPINCTRL, changeNumRows)
    okButton.Bind(wx.EVT_BUTTON, lambda e: frame.Close())

    frame.ShowModal()


def _listDialogWidget(parent, hasProps, propObj, propVal):
    """Creates and returns a GUI panel containing two buttons which, when
    pushed, display dialogs allowing the user to edit the values contained
    in the list.

    See the :func:`_pasteDataDialog` and :func:`_editListDialog` functions.
    """

    panel = wx.Panel(parent)

    # When the user pushes this button on the parent window,
    # a new window is displayed, allowing the user to edit
    # the values in the list individually
    editButton = wx.Button(panel, label='Edit')
    editButton.Bind(
        wx.EVT_BUTTON, lambda ev: _editListDialog(parent, hasProps, propObj))

    # When the user pushes this button, a new window is
    # displayed, allowing the user to type/paste bulk data
    pasteButton = wx.Button(panel, label='Paste data')
    pasteButton.Bind(
        wx.EVT_BUTTON, lambda ev: _pasteDataDialog(parent, hasProps, propObj))

    sizer = wx.BoxSizer(wx.HORIZONTAL)
    panel.SetSizer(sizer)

    sizer.Add(editButton,  flag=wx.EXPAND)
    sizer.Add(pasteButton, flag=wx.EXPAND)

    panel.Layout()

    return panel


def _listEmbedWidget(parent, hasProps, propObj, propVal):

    if not isinstance(propObj._listType, (ptypes.String,
                                          ptypes.Int,
                                          ptypes.Real)):
        raise RuntimeError('Unsupported property '
                           'type: {}'.format(propObj.__class__))

    widget = elistbox.EditableListBox(
        parent,
        ['{}'.format(v) for v in propVal],
        style=(elistbox.ELB_NO_ADD    |
               elistbox.ELB_NO_REMOVE |
               elistbox.ELB_EDITABLE))

    changeTriggeredByWidget = [False]

    def _listBoxMove(ev):
        changeTriggeredByWidget[0] = True
        propVal.move(ev.oldIdx, ev.newIdx)
        changeTriggeredByWidget[0] = False

    def _listBoxEdit(ev):
        changeTriggeredByWidget[0] = True
        propVal[ev.idx] = ev.label
        changeTriggeredByWidget[0] = False

    def _listChanged(*a):

        if changeTriggeredByWidget[0]:
            return

        sel = widget.GetSelection()
        widget.Clear()
        for val in propVal:
            widget.Append('{}'.format(val))

        if sel < widget.GetCount():
            widget.SetSelection(sel)
        else:
            widget.SetSelection(widget.GetCount() - 1)

    widget.Bind(elistbox.EVT_ELB_MOVE_EVENT,   _listBoxMove)
    widget.Bind(elistbox.EVT_ELB_EDIT_EVENT,   _listBoxEdit)

    propVal.addListener('widgets_list_py_{}'.format(id(widget)),
                        _listChanged,
                        weak=False)

    return widget


def _List(parent, hasProps, propObj, propVal):

    if propObj.embed:
        return _listEmbedWidget(parent, hasProps, propObj, propVal)
    else:
        return _listDialogWidget(parent, hasProps, propObj, propVal)
