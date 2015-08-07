#!/usr/bin/env python
#
# bitmapradio.py -
#
# Author: Paul McCarthy <pauldmccarthy@gmail.com>
#

import wx
import wx.lib.newevent as wxevent

_BitampRadioEvent, _EVT_BITMAP_RADIO_EVENT = wxevent.NewEvent()


EVT_BITMAP_RADIO_EVENT = _EVT_BITMAP_RADIO_EVENT


BitmapRadioEvent = _BitampRadioEvent


class BitmapRadioBox(wx.PyPanel):

    def __init__(self, parent, maxSize=None, style=None):
        """
        :arg style: ``wx.HORIZONTAL`` or ``wx.VERTICAL``.
        """
        wx.PyPanel.__init__(self, parent)

        if style   is None: style   = wx.HORIZONTAL
        if maxSize is None: maxSize = 32

        if style & wx.VERTICAL: szorient = wx.VERTICAL
        else:                   szorient = wx.HORIZONTAL

        self.__maxSize    = maxSize
        self.__selection  = -1
        self.__buttons    = []
        self.__clientData = []
        self.__sizer      = wx.BoxSizer(szorient)

        self.SetSizer(self.__sizer)


    def __loadBitmap(self, imgFile):
        
        img     = wx.Image(imgFile)
        maxSize = self.__maxSize

        if maxSize is not None:
            w, h = img.GetSize().Get()

            if w >= h:
                h = maxSize * h / float(w)
                w = maxSize
            else:
                w = maxSize * (w / float(h)) 
                h = maxSize

            img.Rescale(w, h, wx.IMAGE_QUALITY_BICUBIC)

        return wx.BitmapFromImage(img)


    def AddChoice(self, imgFile, clientData=None):

        bmp    = self.__loadBitmap(imgFile)

        # BU_NOTEXT causes a segfault under OSX
        if wx.Platform == '__WXMAC__': style = wx.BU_EXACTFIT
        else:                          style = wx.BU_EXACTFIT | wx.BU_NOTEXT
        
        button = wx.ToggleButton(self, style=style)
        button.SetBitmap(bmp)

        self.__buttons   .append(button)
        self.__clientData.append(clientData)

        self.__sizer.Add(button)
        self.Layout()

        button.Bind(wx.EVT_TOGGLEBUTTON, self.__onButton)

        
    def Clear(self):

        self.__sizer.Clear(True)
        self.__selection  = -1
        self.__buttons    = []
        self.__clientData = []

        
    def Set(self, imgFiles, clientData=None):

        if clientData is None:
            clientData = [None] * len(imgFiles)

        self.Clear()
        map(self.AddChoice, imgFiles, clientData)


    def GetSelection(self):
        return self.__selection

    
    def SetSelection(self, index):

        if index < 0 or index >= len(self.__buttons):
            raise ValueError('Invalid index {}'.format(index))

        self.__selection = index
        
        for i, button in enumerate(self.__buttons):

            if i == index: button.SetValue(True)
            else:          button.SetValue(False)


    def __onButton(self, ev):

        idx  = self.__buttons.index(ev.GetEventObject())
        data = self.__clientData[idx]

        self.SetSelection(idx)
        
        wx.PostEvent(self, BitmapRadioEvent(index=idx, clientData=data))
