# AvsP - an AviSynth editor
# Copyright 2007 Peter Jang
#  http://www.avisynth.org/qwerpoi

#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA, or visit
#  http://www.gnu.org/copyleft/gpl.html .

# Dependencies:
#     Python (tested with v2.7.1)
#     wxPython (tested with v2.8.12 unicode)
# Scripts:
#     wxp.py (general wxPython framework classes)
#     avisynth.py (python Avisynth wrapper)
#     pyavs.py (python AVI support through Avisynth routines)
#     pyavs_avifile.py (python AVI support through Windows AVIFile routines)
#     AvsP_icon.py (icons embedded in a python script)
#     next_icon.py
#     play_icon.py

import os
import sys
import traceback
import cPickle
import string
import codecs
import re
import random, subprocess, math, copy
import socket
import thread
import StringIO
import textwrap
import ctypes
import _winreg
import _md5 as md5
import __builtin__
from collections import OrderedDict, Iterable, Sequence, MutableSequence

if hasattr(sys,'frozen'):
    programdir = os.path.dirname(sys.executable)
    sys.path.insert(0, programdir)
messages = None
def _(s):
    if messages:
        s2 = messages.get(s, s)
        if s2:
            return s2
    return s
__builtin__._ = _
encoding = sys.getfilesystemencoding()

import wx
from wx import stc
import wx.lib.buttons as wxButtons
import  wx.lib.colourselect as  colourselect
import wxp
try:
    import avisynth
except WindowsError, err:
    message = "%sLoad avisynth.dll failed!\nTry install or re-install Avisynth firstly." % err
    app = wx.PySimpleApp()
    wx.MessageBox(message, 'Windows Error', wx.OK|wx.ICON_ERROR)
    sys.exit(0)
try:
    import pyavs
except AttributeError:
    import pyavs_avifile as pyavs
from icons import AvsP_icon, next_icon, play_icon, skip_icon, spin_icon,\
                  ok_icon, smile_icon, question_icon, rectangle_icon,\
                  dragdrop_cursor

version = '2.2.1'

try:
    from __translation_new import new_translation_string
except ImportError:
    if hasattr(sys,'frozen'):
        raise
    else:
        import AvsP_i18n
        AvsP_i18n.main(version)
        from __translation_new import new_translation_string

# Custom styled text control for avisynth language
class AvsStyledTextCtrl(stc.StyledTextCtrl):
    STC_AVS_DEFAULT = stc.STC_LUA_DEFAULT
    STC_AVS_COMMENT = stc.STC_LUA_COMMENT
    STC_AVS_ENDCOMMENT = stc.STC_LUA_COMMENTLINE
    STC_AVS_BLOCKCOMMENT = stc.STC_LUA_COMMENTDOC
    STC_AVS_NUMBER = stc.STC_LUA_NUMBER
    STC_AVS_NUMBERBAD = stc.STC_LUA_CHARACTER
    STC_AVS_OPERATOR = stc.STC_LUA_OPERATOR
    STC_AVS_STRING = stc.STC_LUA_STRING
    STC_AVS_STRINGEOL = stc.STC_LUA_STRINGEOL
    STC_AVS_TRIPLE = stc.STC_LUA_LITERALSTRING
    STC_AVS_COREFILTER = stc.STC_LUA_WORD
    STC_AVS_PLUGIN = stc.STC_LUA_WORD2
    STC_AVS_CLIPPROPERTY = stc.STC_LUA_WORD3
    STC_AVS_USERFUNCTION = stc.STC_LUA_WORD4
    STC_AVS_USERSLIDER = stc.STC_LUA_WORD5
    STC_AVS_SCRIPTFUNCTION = stc.STC_LUA_WORD6
    STC_AVS_KEYWORD = stc.STC_LUA_WORD7
    STC_AVS_MISCWORD = stc.STC_LUA_WORD8
    STC_AVS_DATATYPE = stc.STC_LUA_PREPROCESSOR
    STC_AVS_IDENTIFIER = stc.STC_LUA_IDENTIFIER
    finddata = wx.FindReplaceData(wx.FR_DOWN)
    replacedata = wx.FindReplaceData(wx.FR_DOWN)
    def __init__(self, parent, app, id=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.DefaultSize, style=wx.SIMPLE_BORDER,
            #~ filterDict=None,
            #~ filterPresetDict=None,
            #~ keywordLists=None,
            #~ autocomplete=True,
            #~ autoparentheses=1,
            #~ usestringeol=False,
            #~ syntaxhighlight=True,
            #~ calltips=True,
            #~ frequentcalltips=True,
            #~ usetabs=False,
            #~ tabwidth=4,
            #~ highlightline=False,
            #~ highlightlinecolor=(232,232,255),
            #~ wrap=False,
            #~ numlinechars=0,
            #~ usemonospacedfont=False,
            #~ textstyles=None,
            ):
        stc.StyledTextCtrl.__init__(self, parent, id, pos, size, style)
        self.app = app
        self.SetUserOptions()
        self.SetEOLMode(stc.STC_EOL_LF)
        #~ self.CmdKeyClear(stc.STC_KEY_TAB,0)
        self.UsePopUp(0)
        self.showLinenumbers = 1
        #~ self.enableFolding = 1
        #~ self.finddata = wx.FindReplaceData(wx.FR_DOWN)
        #~ self.replacedata = wx.FindReplaceData(wx.FR_DOWN)
        self.calltipFilter = None
        self.calltiptext = None
        self.calltipOpenpos = None
        self.flagTextChanged = self.flagCodeFolding = False
        self.keywordStyleList = (
            self.STC_AVS_COREFILTER,
            #~ self.STC_AVS_CLIPPROPERTY,
            self.STC_AVS_PLUGIN,
            self.STC_AVS_USERFUNCTION,
            #~ self.STC_AVS_SCRIPTFUNCTION,
        )
        self.highlightwordStyleList = (
            self.STC_AVS_COREFILTER,
            self.STC_AVS_CLIPPROPERTY,
            self.STC_AVS_PLUGIN,
            self.STC_AVS_USERFUNCTION,
            self.STC_AVS_SCRIPTFUNCTION,
        )
        self.commentStyle = [self.STC_AVS_COMMENT, self.STC_AVS_BLOCKCOMMENT, self.STC_AVS_ENDCOMMENT]
        self.nonBraceStyles = [
            self.STC_AVS_COMMENT,
            self.STC_AVS_ENDCOMMENT,
            self.STC_AVS_BLOCKCOMMENT,
            self.STC_AVS_STRING,
            self.STC_AVS_TRIPLE,
            self.STC_AVS_STRINGEOL,
            self.STC_AVS_USERSLIDER,
        ]
        # Auto-completion options
        self.AutoCompSetIgnoreCase(1)
        self.AutoCompSetDropRestOfWord(1)
        self.AutoCompSetAutoHide(1)
        self.AutoCompSetChooseSingle(0)
        self.AutoCompSetCancelAtStart(1)
        self.AutoCompStops(''' `~!@#$%^&*()+=[]{};:'",<.>/?\|''')
        # Margin options
        #~ self.SetMarginType(0, stc.STC_MARGIN_NUMBER)
        self.SetMarginWidth(0, self.initialMarginWidth)
        self.SetMarginWidth(1, 0)
        self.SetMarginType(2, stc.STC_MARGIN_SYMBOL)
        self.SetMarginMask(2, stc.STC_MASK_FOLDERS)
        self.SetMarginSensitive(2, True)        
        self.SetMarginWidth(2, 13)
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPEN,    stc.STC_MARK_MINUS, "white", "black")
        self.MarkerDefine(stc.STC_MARKNUM_FOLDER,        stc.STC_MARK_PLUS,  "white", "black")
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERSUB,     stc.STC_MARK_EMPTY, "white", "black")
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERTAIL,    stc.STC_MARK_EMPTY, "white", "black")
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEREND,     stc.STC_MARK_EMPTY, "white", "black")
        self.MarkerDefine(stc.STC_MARKNUM_FOLDEROPENMID, stc.STC_MARK_EMPTY, "white", "black")
        self.MarkerDefine(stc.STC_MARKNUM_FOLDERMIDTAIL, stc.STC_MARK_EMPTY, "white", "black")
        #~ self.SetMarginWidth(2, 0)
        self.fitNumberMarginWidth()
        self.SetSavePoint()
        # Event handling
        self.Bind(stc.EVT_STC_UPDATEUI, self.OnUpdateUI)
        self.Bind(stc.EVT_STC_CHANGE, self.OnTextChange)
        self.Bind(stc.EVT_STC_CHARADDED, self.OnTextCharAdded)
        self.Bind(stc.EVT_STC_NEEDSHOWN, self.OnNeedShown)
        self.Bind(wx.EVT_KEY_UP, self.OnKeyUp)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        #~ self.Bind(wx.EVT_FIND, self.OnFindPressed)
        #~ self.Bind(wx.EVT_FIND_NEXT, self.OnFindPressed)
        #~ self.Bind(wx.EVT_FIND_REPLACE, self.OnReplacePressed)
        #~ self.Bind(wx.EVT_FIND_REPLACE_ALL, self.OnReplaceAllPressed)
        #~ self.Bind(wx.EVT_FIND_CLOSE, self.OnFindClose)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnLeftMouseDown)
        self.Bind(stc.EVT_STC_CALLTIP_CLICK, self.OnCalltipClick)
        self.Bind(wx.EVT_KILL_FOCUS, self.OnKillFocus)
        self.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
        self.Bind(stc.EVT_STC_MARGINCLICK, self.OnMarginClick)
        try:
            self.Bind(wx.EVT_MOUSE_CAPTURE_LOST, lambda event: self.ReleaseMouse())
        except AttributeError:
            pass
        if self.GetLexer() == stc.STC_LEX_CONTAINER:
            self.Bind(stc.EVT_STC_STYLENEEDED, self.OnStyleNeeded)

    def SetUserOptions(self):
        # AviSynth filter information
        #~ if not filterDict:
            #~ filterDict = self.defineFilterDict()
            #~ filterDict = dict([(name.lower(), (name,args,ftype)) for name, (args,ftype) in filterDict.items()])
        #~ if not keywordLists:
            #~ keywords = ['default', 'end', 'return', 'global', 'function', 'last', 'true', 'false', 'try', 'catch',]
            #~ datatypes = ['clip', 'int', 'float', 'string', 'bool', 'val']
            #~ operators = ('-', '*', ',', '.', '/', ':', '?', '\\', '+', '<', '>', '=', '(', ')', '[', ']', '{', '}', '!', '%', '&', '|')
            #~ miscwords = []
            #~ keywordLists = (keywords, datatypes, operators, miscwords)
        if self.app.options['syntaxhighlight']:
            self.SetTextStyles(self.app.options['textstyles'], self.app.options['usemonospacedfont'])
        else:
            self.setStylesNoColor()
        if self.app.options['autocompleteicons']:            
            self.RegisterImage(1, ok_icon.GetBitmap())
            self.RegisterImage(2, smile_icon.GetBitmap())
            self.RegisterImage(3, question_icon.GetBitmap())            
            self.RegisterImage(4, rectangle_icon.GetBitmap())
        else:
            self.ClearRegisteredImages()
        # General options
        self.SetUseTabs(self.app.options['usetabs'])
        self.SetTabWidth(self.app.options['tabwidth'])
        self.SetCaretLineBack(self.app.options['textstyles']['highlightline'].split(':')[1])
        self.SetCaretLineVisible(self.app.options['highlightline'])
        if self.app.options['wrap']:
            self.SetWrapMode(stc.STC_WRAP_WORD)
        else:
            self.SetWrapMode(stc.STC_WRAP_NONE)
        self.SetFoldFlags(self.app.options['foldflag']<<4)
        self.initialMarginWidth = self.numlinechars2pixels(self.app.options['numlinechars'])
        self.fitNumberMarginWidth()
        self.Colourise(0, self.GetTextLength())
        

    def defineFilterDict(self):
        return {
            'AddBorders': ('(clip, int left, int top, int right, int bottom, int color)', 0),
            'Amplify': ('(clip, float amount1 [, ...])', 0),
            'AmplifydB': ('(clip, float amount1 [, ...])', 0),
            'Animate': ('(clip, int start_frame, int end_frame, string filtername, start_args, end_args)', 0),
            'ApplyRange': ('(clip, int start_frame, int end_frame, string filtername, args)', 0),
            'AssumeFrameBased': ('(clip)', 0),
            'AssumeFieldBased': ('(clip)', 0),
            'AssumeBFF': ('(clip)', 0),
            'AssumeTFF': ('(clip)', 0),
            'AssumeSampleRate': ('(clip, int samplerate)', 0),
            'AudioDub': ('(video_clip, audio_clip)', 0),
            'AVISource': ('(string filename [, ...], bool "audio", string "pixel_type")', 0),
            'OpenDMLSource': ('(string filename [, ...], bool "audio", string "pixel_type")', 0),
            'AVIFileSource': ('(string filename [, ...], bool "audio", string "pixel_type")', 0),
            'WAVSource': ('(string filename [, ...])', 0),
            'BlankClip': ('(clip clip, int "length", int "width", int "height", string "pixel_type",\nfloat "fps", int "fps_denominator", int "audio_rate", bool "stereo",\nbool "sixteen_bit", int "color")', 0),
            'Blackness': ('(clip clip, int "length", int "width", int "height", string "pixel_type",\nfloat "fps", int "fps_denominator", int "audio_rate", bool "stereo",\nbool "sixteen_bit", int "color")', 0),
            'Blur': ('(clip, float amount)', 0),
            'Sharpen': ('(clip, float amount)', 0),
            'Bob': ('(clip, float "b", float "c", float "height")', 0),
            'ColorBars': ('(int width, int height)', 0),
            'ColorYUV': ('(clip, float "gain_y", float "off_y", float "gamma_y", float "cont_y",\nfloat "gain_u", float "off_u", float "gamma_u", float "cont_u", float "gain_v",\nfloat "off_v", float "gamma_v", float "cont_v", string "levels", string "opt",\nbool "showyuv", bool "analyze", bool "autowhite", bool "autogain")', 0),
            'ComplementParity': ('(clip)', 0),
            'Compare': ('(clip_filtered, clip_original, string "channels", string "logfile", bool "show_graph")', 0),
            'ConditionalFilter': ('(clip testclip, clip source1, clip source2, string filter,\nstring operator, string value, bool ''show'')', 0),
            'FrameEvaluate': ('(clip clip, script function, bool "after_frame")', 0),
            'ScriptClip': ('(clip clip, string function, bool ''show'')', 0),
            'ConditionalReader': ('(clip clip, string filename, string variablename, bool "show")', 0),
            'ConvertBackToYUY2': ('(clip, bool "interlaced")', 0),
            'ConvertToRGB': ('(clip, bool "interlaced")', 0),
            'ConvertToRGB24': ('(clip, bool "interlaced")', 0),
            'ConvertToRGB32': ('(clip, bool "interlaced")', 0),
            'ConvertToYUY2': ('(clip, bool "interlaced")', 0),
            'ConvertToYV12': ('(clip, bool "interlaced")', 0),
            'ConvertAudioTo8bit': ('(clip)', 0),
            'ConvertAudioTo16bit': ('(clip)', 0),
            'ConvertAudioTo24bit': ('(clip)', 0),
            'ConvertAudioTo32bit': ('(clip)', 0),
            'ConvertAudioToFloat': ('(clip)', 0),
            'ConvertToMono': ('(clip)', 0),
            'Crop': ('(clip, int left, int top, int -right, int -bottom, bool "align")', 0),
            'CropBottom': ('(clip, int count, bool "align")', 0),
            'DelayAudio': ('(clip, float seconds)', 0),
            'DeleteFrame': ('(clip, int frame)', 0),
            'DirectShowSource': ('(string filename, int "fps", bool "seek", bool "audio", bool "video")', 0),
            'Dissolve': ('(clip1, clip2 [, ...], int overlap)', 0),
            'DoubleWeave': ('(clip)', 0),
            'DuplicateFrame': ('(clip, int frame)', 0),
            'EnsureVBRMP3Sync': ('(clip)', 0),
            'FadeOut': ('(clip, int frames, int "color")', 0),
            'FadeOut2': ('(clip, int frames, int "color")', 0),
            'FadeIn': ('(clip, int frames, int "color")', 0),
            'FadeIn2': ('(clip, int frames, int "color")', 0),
            'FadeIO': ('(clip, int frames, int "color")', 0),
            'FadeIO2': ('(clip, int frames, int "color")', 0),
            'FixBrokenChromaUpsampling': ('(clip)', 0),
            'FixLuminance': ('(clip, int intercept, int slope)', 0),
            'FlipHorizontal': ('(clip)', 0),
            'FlipVertical': ('(clip)', 0),
            'AssumeFPS': ('(clip, float fps, bool "sync_audio")', 0),
            'ChangeFPS': ('(clip, float fps, bool "linear")', 0),
            'ConvertFPS': ('(clip, int new_rate, int "zone", int "vbi")', 0),
            'FreezeFrame': ('(clip, int first_frame, int last_frame, int source_frame)', 0),
            'GeneralConvolution': ('(clip, int "bias", string matrix)', 0),
            'GetChannel': ('(clip, int ch1 [, int ch2, ...])', 0),
            'Greyscale': ('(clip)', 0),
            'Histogram': ('(clip, string ''mode'')', 0),
            'ImageReader': ('(string path, int begin, int end, int fps, bool "use_DevIL")', 0),
            'ImageWriter': ('(clip, string "path", int "begin", int "end", string format)', 0),
            'Info': ('(clip)', 0),
            'Interleave': ('(clip1, clip2 [, ...])', 0),
            'Invert': ('(clip, string "channels")', 0),
            'KillAudio': ('(clip)', 0),
            'Layer': ('(clip, layer_clip, string "op", int "level", int "x", int "y", int "threshold",\nbool "use_chroma")', 0),
            'Mask': ('(clip, mask_clip)', 0),
            'ResetMask': ('(clip)', 0),
            'ColorKeyMask': ('(clip, int color, int tolerance)', 0),
            'Letterbox': ('(clip, int top, int bottom, [int left, int right])', 0),
            'Levels': ('(clip, int input_low, float gamma, int input_high, int output_low, int\noutput_high, bool "coring")', 0),
            'Limiter': ('(clip, int ''min_luma'', int ''max_luma'', int ''min_chroma'', int ''max_chroma'')', 0),
            'LoadPlugin': ('(string filename)', 0),
            'Loop': ('(clip, int "times", int "start", int "end")', 0),
            'MergeChannels': ('(clip1, clip2 [, ...])', 0),
            'MergeChroma': ('(clip1, clip2, float weight)', 0),
            'MergeLuma': ('(clip1, clip2, float weight)', 0),
            'MessageClip': ('(string message, int "width", int "height", bool "shrink", int "text_color",\nint "halo_color", int "bg_color")', 0),
            'MixAudio': ('(clip1, clip 2, clip1_factor, "clip2_factor")', 0),
            'Normalize': ('(clip, float "volume", bool "show")', 0),
            'Overlay': ('(clip, clip overlay, int ''x'', int ''y'', clip ''mask'', float ''opacity'',\nstring ''mode'', bool ''greymask'', string ''output'', bool ''ignore_conditional'',\nbool ''pc_range'')', 0),
            'PeculiarBlend': ('(clip, int cutoff)', 0),
            'Pulldown': ('(clip, int a , int b)', 0),
            'RGBAdjust': ('(clip, float red, float green, float blue, float alpha)', 0),
            'HorizontalReduceBy2': ('(clip)', 0),
            'VerticalReduceBy2': ('(clip)', 0),
            'ReduceBy2': ('(clip)', 0),
            'ResampleAudio': ('(clip, int new_sample_rate)', 0),
            'BilinearResize': ('(clip, int target_width, int target_height)', 0),
            'BicubicResize': ('(clip, int target_width, int target_height, float "b", float "c")', 0),
            'LanczosResize': ('(clip, int target_width, int target_height)', 0),
            'PointResize': ('(clip, int target_width, int target_height)', 0),
            'Reverse': ('(clip)', 0),
            'SegmentedAVISource': ('(string base_filename [, ...], bool "audio")', 0),
            'SegmentedDirectShowSource': ('(string base_filename [, ...] [, fps])', 0),
            'SelectEven': ('(clip)', 0),
            'SelectOdd': ('(clip)', 0),
            'SelectEvery': ('(clip, int step_size, int offset1 [, int offset2 [, ...]])', 0),
            'SelectRangeEvery': ('(clip, int period, int range)', 0),
            'SeparateFields': ('(clip)', 0),
            'ShowAlpha': ('(clip, string pixel_type)', 0),
            'ShowFiveVersions': ('(clip1, clip2, clip3, clip4, clip5)', 0),
            'ShowFrameNumber': ('(clip, bool "scroll")', 0),
            'ShowSMPTE': ('(clip, float fps)', 0),
            'SpatialSoften': ('(clip, int radius, int luma_threshold, int chroma_threshold)', 0),
            'TemporalSoften': ('(clip, int radius, int luma_threshold, int chroma_threshold, int "scenechange",\nint "mode")', 0),
            'AlignedSplice': ('(clip1, clip2 [, ...])', 0),
            'UnAlignedSplice': ('(clip1, clip2 [, ...])', 0),
            'SSRC': ('(int samplerate, bool "fast")', 0),
            'StackHorizontal': ('(clip1, clip2 [, ...])', 0),
            'StackVertical': ('(clip1, clip2 [, ...])', 0),
            'Subtitle': ('(clip, string text, int "x", int "y", int "first_frame", int "last_frame",\nstring "font", int "size", int "text_color", int "halo_color")', 0),
            'Subtract': ('(clip1, clip2)', 0),
            'SuperEQ': ('(string filename)', 0),
            'SwapUV': ('(clip)', 0),
            'UToY': ('(clip)', 0),
            'VToY': ('(clip)', 0),
            'YToUV': ('(clip)', 0),
            'SwapFields': ('(clip)', 0),
            'Tone': ('(float "length", float "frequency", int "samplerate", int "channels", string "type")', 0),
            'Trim': ('(clip, int first_frame, int last_frame)', 0),
            'TurnLeft': ('(clip)', 0),
            'TurnRight': ('(clip)', 0),
            'Tweak': ('(clip, float "hue", float "sat", float "bright", float "cont", bool "coring")', 0),
            'Version': ('()', 0),
            'Weave': ('(clip)', 0),
        }

        #~ # Currently FunctionNames, ClipProperties, and KeyWords are unused
        #~ self.FunctionNames = ['floor', 'ceil', 'round', 'int', 'float', 'frac', 'abs', 'sign',
                                       #~ 'hexvalue', 'sin', 'cos', 'pi', 'log', 'exp', 'pow', 'sqrt', 'rand', 'spline',
                                       #~ 'ucase', 'lcase', 'revstr', 'strlen', 'findstr', 'leftstr', 'midstr',
                                       #~ 'versionnumber', 'versionstring', 'chr', 'time', 'value', 'string',
                                       #~ 'isbool', 'isint', 'isfloat', 'isstring', 'isclip',
                                       #~ 'select', 'defined', 'default', 'exist', 'eval', 'apply', 'import', 'try', 'catch',
                                       #~ 'setmemorymax', 'setworkingdir']
        #~ self.ClipProperties = ['width', 'height', 'framecount', 'framerate',
                                     #~ 'audiorate', 'audiolength', 'audiochannels', 'audiobits',
                                     #~ 'isrgb', 'isrgb24', 'isrgb32', 'isyuy2', 'isyuv',
                                     #~ 'isplanar', 'isinterleaved', 'isfieldbased', 'isframebased', 'getparity']
        #~ self.KeyWords = tuple(' '.join(self.FilterNames).lower().split(' '))

    def SetTextStyles(self, textstyles, monospaced=False):
        self.SetLexer(stc.STC_LEX_CONTAINER)
        #~ self.commentStyle = [self.STC_AVS_COMMENT, self.STC_AVS_BLOCKCOMMENT, self.STC_AVS_ENDCOMMENT]
        #~ self.nonBraceStyles = [
            #~ self.STC_AVS_COMMENT,
            #~ self.STC_AVS_ENDCOMMENT,
            #~ self.STC_AVS_BLOCKCOMMENT,
            #~ self.STC_AVS_STRING,
            #~ self.STC_AVS_TRIPLE,
            #~ self.STC_AVS_STRINGEOL,
            #~ self.STC_AVS_USERSLIDER,
        #~ ]
        styleInfo = (
            (self.STC_AVS_DEFAULT, 'default', ''),
            (self.STC_AVS_COMMENT, 'comment', ',eol'),
            (self.STC_AVS_ENDCOMMENT, 'endcomment', ''),
            (self.STC_AVS_BLOCKCOMMENT, 'blockcomment', ''),
            (self.STC_AVS_NUMBER, 'number', ''),
            (self.STC_AVS_STRING, 'string', ''),
            (self.STC_AVS_TRIPLE, 'stringtriple', ''),
            (self.STC_AVS_COREFILTER, 'internalfilter', ''),
            (self.STC_AVS_PLUGIN, 'externalfilter', ''),
            (self.STC_AVS_CLIPPROPERTY, 'clipproperty', ''),
            (self.STC_AVS_USERFUNCTION, 'userdefined', ''),
            (self.STC_AVS_OPERATOR, 'operator', ''),
            (self.STC_AVS_STRINGEOL, 'stringeol', ',eol'),
            (self.STC_AVS_USERSLIDER, 'userslider', ''),

            (self.STC_AVS_SCRIPTFUNCTION, 'internalfunction', ''),
            (self.STC_AVS_KEYWORD, 'keyword', ''),
            (self.STC_AVS_MISCWORD, 'miscword', ''),

            (stc.STC_STYLE_LINENUMBER, 'linenumber', ''),
            (stc.STC_STYLE_BRACELIGHT, 'bracelight', ''),
            (stc.STC_STYLE_BRACEBAD, 'badbrace', ''),
            (self.STC_AVS_NUMBERBAD, 'badnumber', ''),

            (self.STC_AVS_DATATYPE, 'datatype', ''),
        )
        default = 'font:Arial, size:10, fore:#000000, back:#FFFFFF'

        # Global default styles for all languages
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT, textstyles.get('default', default))
        #~ if textstyles.get('default', default).endswith('bold'):
            #~ self.StyleSetBold(stc.STC_STYLE_DEFAULT, 1)
        #~ else:
            #~ self.StyleSetBold(stc.STC_STYLE_DEFAULT, 0)
        if monospaced:
            face = ''
            size = ''
            for item in textstyles['monospaced'].split(','):
                if item.lower().startswith('face:'):
                    face = item.split(':')[1]
                if item.lower().startswith('size:'):
                    size = int(item.split(':')[1])
            self.StyleSetFaceName(stc.STC_STYLE_DEFAULT, face)
            self.StyleSetSize(stc.STC_STYLE_DEFAULT, size)
        self.StyleClearAll()  # Reset all to be like the default

        for style, key, extra in styleInfo:
            self.StyleSetSpec(style, textstyles.get(key, default) + extra)
            if monospaced:
                self.StyleSetFaceName(style, face)
                self.StyleSetSize(style, size)
        # Set miscellaneous non-style colors
        for key in ('calltip', 'calltiphighlight'):
            value = textstyles[key]
            for elem in value.split(','):
                if elem.startswith('fore:'):
                    if key == 'calltip':
                        self.CallTipSetForeground(elem.split(':')[1].strip())
                    else:
                        self.CallTipSetForegroundHighlight(elem.split(':')[1].strip())
                if elem.startswith('back:'):
                    self.CallTipSetBackground(elem.split(':')[1].strip())
        self.SetCaretForeground(textstyles['cursor'].split(':')[1])
        #~ self.SetSelForeground(True, '#00FF00')
        self.SetSelBackground(True, textstyles['highlight'].split(':')[1])
        clr = textstyles['foldmargin'].split(':')[1]
        self.SetFoldMarginColour(True, clr)
        self.SetFoldMarginHiColour(True, clr)
        

    def setStylesNoColor(self):
        # unfold and remove fold points if script is already existing
        for lineNum in range(self.GetLineCount()):
            if self.GetFoldLevel(lineNum) & stc.STC_FOLDLEVELHEADERFLAG and not self.GetFoldExpanded(lineNum):
                self.SetFoldExpanded(lineNum, True)
                self.Expand(lineNum, True)
            self.SetFoldLevel(lineNum, stc.STC_FOLDLEVELBASE)
        #~ self.SetKeyWords(0, ' '.join(self.FilterNames).lower())
        self.SetLexer(stc.STC_LEX_NULL)
        #~ self.commentStyle = stc.STC_MATLAB_COMMENT

        #~ mainfont = 'Arial'
        #~ mainsize = 10
        #~ commentfont = 'Comic Sans MS'
        #~ commentsize = 9
        #~ s_text = {'font': mainfont, 'size': mainsize, 'color': '#000000'}
        #~ s_comment = {'font': commentfont, 'size': commentsize, 'color': '#007F00'}
        #~ s_string = {'font': 'Times New Roman', 'size': mainsize, 'color': '#7F007F'}
        #~ s_filter = {'font': mainfont, 'size': mainsize, 'color': '#00007F'}
        #~ s_function = {'font': mainfont, 'size': mainsize, 'color': '#0000AA'}

        # Global default styles for all languages
        default = 'font:Arial, size:10, fore:#000000, back:#FFFFFF'
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT, self.app.options['textstyles'].get('default', default))
        if self.app.options['usemonospacedfont']:
            for item in self.app.options['textstyles']['monospaced'].split(','):
                if item.lower().startswith('face:'):
                    face = item.split(':')[1]
                if item.lower().startswith('size:'):
                    size = int(item.split(':')[1])
            self.StyleSetFaceName(stc.STC_STYLE_DEFAULT, face)
            self.StyleSetSize(stc.STC_STYLE_DEFAULT, size)
        self.StyleClearAll()  # Reset all to be like the default

    def numlinechars2pixels(self, numlinechars):
        return self.TextWidth(stc.STC_STYLE_LINENUMBER, '%s' % ('0'*numlinechars)) + 12

    def fitNumberMarginWidth(self):
        # Update line number margin width
        w = self.TextWidth(stc.STC_STYLE_LINENUMBER, '%s' % str(self.GetLineCount())) + 12
        w = max(w, self.initialMarginWidth)
        if w != self.GetMarginWidth(0):
            self.SetMarginWidth(0, w)

    # New utility functions
    def ShowFindDialog(self):
        if hasattr(self, 'frdlg'):
            return
        text = self.GetTextRange(self.GetSelectionStart(), self.GetSelectionEnd())
        if text != '':
            self.finddata.SetFindString(text)
        AvsStyledTextCtrl.frdlg = wx.FindReplaceDialog(self.GetParent(), self.finddata, _('Find'))
        self.frdlg.Show()
        
    def ShowReplaceDialog(self):
        if hasattr(self, 'frdlg'):
            return
        text = self.GetTextRange(self.GetSelectionStart(), self.GetSelectionEnd())
        if text != '':
            self.replacedata.SetFindString(text)
        AvsStyledTextCtrl.frdlg = wx.FindReplaceDialog(self.GetParent(), self.replacedata, _('Replace'), wx.FR_REPLACEDIALOG)
        self.frdlg.Show()
    
    def FindNext(self):
        self.OnFindNext(self)

    def IndentSelection(self):
        self.CmdKeyExecute(stc.STC_CMD_TAB)

    def UnIndentSelection(self):
        self.CmdKeyExecute(stc.STC_CMD_BACKTAB)

    def BlockComment(self):
        line1 = self.LineFromPosition(self.GetSelectionStart())
        line2 = self.LineFromPosition(self.GetSelectionEnd())
        self.BeginUndoAction()
        for line in xrange(line1, line2+1):
            txt = self.GetLine(line)
            if txt.strip():
                pos = self.PositionFromLine(line) + len(txt) - len(txt.lstrip())
                if txt.strip().startswith('#~ '):
                    self.SetTargetStart(pos)
                    self.SetTargetEnd(pos+3)
                    self.ReplaceTarget('')
                else:
                    self.SetTargetStart(pos)
                    self.SetTargetEnd(pos)
                    self.ReplaceTarget('#~ ')
        self.EndUndoAction()
        
    def StyleComment(self):
        pos = self.GetCurrentPos()
        start = self.PositionFromLine(self.LineFromPosition(pos))
        style = self.GetStyleAt(pos)
        if style == self.STC_AVS_COMMENT:
            while pos > start and self.GetStyleAt(pos-1) == self.STC_AVS_COMMENT:
                pos -= 1
            self.SetTargetStart(pos)
            if self.GetTextRange(pos, pos+3) == '#~ ':                
                self.SetTargetEnd(pos+3)
            else:
                self.SetTargetEnd(pos+1)
            self.ReplaceTarget('')
        else:
            if pos > start and unichr(self.GetCharAt(pos)) == '.' and self.GetStyleAt(pos-1) == self.STC_AVS_NUMBER:
                pos -= 1
                style = self.STC_AVS_NUMBER
            while pos > start and self.GetStyleAt(pos-1) == style:
                pos -= 1
            if pos > start and unichr(self.GetCharAt(pos-1)) == '.':
                pos -= 1
            if style == self.STC_AVS_NUMBER:
                while pos > start and self.GetStyleAt(pos-1) == style:
                    pos -= 1
                if pos > start and unichr(self.GetCharAt(pos-1)) in '+-':
                    pos -= 1
            self.InsertText(pos, '#~ ')                

    def MoveSelectionByOneLine(self, up=True):
        selA = self.GetSelectionStart()
        selB = self.GetSelectionEnd()
        line1 = self.LineFromPosition(selA)
        line2 = self.LineFromPosition(selB)
        numlines = self.GetLineCount()
        if line2 == numlines - 1:
            if selB != self.GetLength() or selB != self.PositionFromLine(line2):
                self.InsertText(self.GetLineEndPosition(line2), '\n')
        posA = self.PositionFromLine(line1)
        if self.GetSelectionEnd() == self.PositionFromLine(line2) and selA != selB:
            posB = self.PositionFromLine(line2)
        else:
            posB = self.PositionFromLine(line2 + 1)
        if up:
            newline = max(line1 - 1, 0)
        else:
            newline = min(line1 + 1, numlines-1 - (line2 - line1))
        if newline == line1:
            return
        if newline == self.GetLineCount() - 1 and self.GetLine(newline) != '':
                self.InsertText(self.GetLineEndPosition(newline), '\n')
        self.BeginUndoAction()
        self.SetSelection(posA, posB)
        txt = self.GetSelectedText()
        self.ReplaceSelection('')
        newpos = self.PositionFromLine(newline)
        self.GotoPos(newpos)
        self.ReplaceSelection(txt)
        self.SetSelection(newpos, newpos+len(txt))
        self.EndUndoAction()

    def ShowAutocomplete(self, all=False, auto=0):
        pos = self.GetCurrentPos()
        startwordpos = self.WordStartPosition(pos,1)
        if pos == startwordpos:
            return
        word = self.GetTextRange(startwordpos,pos)
        #~ if len(word) == 0:
            #~ return
        keywords = []
        wordlower = word.lower()
        keywordSublist = self.app.avsazdict.get(word[0].lower())
        if keywordSublist is not None:
            for keyword in keywordSublist:
                if (all or keyword not in self.app.options['autocompleteexclusions']) and keyword.lower().startswith(wordlower):
                    keywords.append(keyword)
        if self.app.options['autocompletevariables']:
            lineCount = self.LineFromPosition(pos)
            line = 0
            while line <= lineCount:
                if line == lineCount:
                    line += 1
                    lineCount = self.GetLineCount()
                    continue
                start = self.PositionFromLine(line)
                eol = self.GetLineEndPosition(line)
                #~ while unichr(self.GetCharAt(eol-1)) == '\\' or unichr(self.GetCharAt(eol+1)) == '\\':
                    #~ line += 1
                    #~ if line >= lineCount:
                        #~ break
                    #~ eol = self.GetLineEndPosition(line)
                while line < lineCount - 1 and (self.FindText(self.PositionFromLine(line), eol, r'\\[ ]*$', stc.STC_FIND_REGEXP) != -1 or \
                                                self.FindText(eol+1, self.GetLineEndPosition(line+1), r'^[ ]*\\', stc.STC_FIND_REGEXP) != -1):
                    line += 1
                    eol = self.GetLineEndPosition(line)
                start = self.FindText(start, eol, r'\<', stc.STC_FIND_REGEXP)
                while start != -1 and self.GetStyleAt(start) == self.STC_AVS_BLOCKCOMMENT:
                    end = self.WordEndPosition(start, 1)
                    start = self.FindText(end, eol, r'\<', stc.STC_FIND_REGEXP)
                if start == -1:
                    line += 1
                    continue
                end = self.WordEndPosition(start, 1)
                keyword = self.GetTextRange(start, end)
                #~ print keyword
                if self.GetStyleAt(start) == self.STC_AVS_DEFAULT and keyword.lower().startswith(wordlower) and keyword not in keywords:
                    keywords.append(keyword)
                elif keyword == 'global' or keyword == 'function':
                    start = self.FindText(end, self.GetLineEndPosition(line), r'\<', stc.STC_FIND_REGEXP)
                    if start == -1:
                        line += 1
                        continue
                    end = self.WordEndPosition(start, 1)
                    keyword = self.GetTextRange(start, end)
                    if keyword.lower().startswith(wordlower) and keyword not in keywords:
                        keywords.append(keyword)
                line += 1
            keywords.sort(key=lambda s: s.lower())
        if keywords:            
            if auto != 2 or (len(keywords) == 1 and len(keywords[0]) != len(word)):
                if self.app.options['autocompleteicons']:
                    for i in range(len(keywords)):
                        keyword = keywords[i].lower()
                        if keyword not in self.app.avsfilterdict:
                            keywords[i] += '?4'
                            continue
                        preset = self.app.options['filterpresets'].get(keyword)
                        if preset is None:
                            for key in self.app.options['filterpresets']:
                                if self.app.avsfilterdict[key][1] == self.STC_AVS_PLUGIN:
                                    index = key.rfind('_'+keyword)
                                    if index != -1 and len(key) == index + 1 + len(keyword):
                                        preset = self.app.options['filterpresets'][key][index+1:]
                                        break
                        if preset is None:
                            preset = self.CreateDefaultPreset(keywords[i])
                        question = preset.count('?')
                        comma = preset.count(',')
                        if question == 0:
                            keywords[i] += '?1'
                        elif question == 1 or question*10 <= (comma+1)*3:
                            keywords[i] += '?2'                        
                        elif comma <= 1:
                            pass
                        elif question*10 >= (comma+1)*7:
                            keywords[i] += '?3'                
                self.AutoCompShow(len(word), ' '.join(keywords))
            #~ if len(keywords) == 1:
                #~ self.FinishAutocomplete()
        elif auto == 0 and pos - startwordpos > 0:
            self.CmdKeyExecute(stc.STC_CMD_CHARLEFT)
            wx.CallAfter(self.ShowAutocomplete)

    def FinishAutocomplete(self, key=None):
        self.AutoCompComplete()
        pos = self.GetCurrentPos()
        startwordpos = self.WordStartPosition(pos,1)
        filtername = self.GetTextRange(startwordpos,pos)
        if filtername.lower() not in self.app.avsfilterdict:
            return
        boolActivatePreset = False
        if self.app.options['presetactivatekey'] == 'tab' and key == wx.WXK_TAB:
            boolActivatePreset = True
        if self.app.options['presetactivatekey'] == 'return' and key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            boolActivatePreset = True
        if boolActivatePreset:
            preset = self.app.options['filterpresets'].get(filtername.lower())
            boolHighlightQuestionMarks = True
            if preset is None:
                for key in self.app.options['filterpresets']:
                    if self.app.avsfilterdict[key][1] == self.STC_AVS_PLUGIN:
                        index = key.find('_'+filtername.lower())
                        if index != -1 and len(key) == index + 1 + len(filtername):
                            preset = self.app.options['filterpresets'][key][index+1:]
                            break
            if preset is not None:
                self.SetSelection(startwordpos, pos)
                self.ReplaceSelection(preset)
                cursorTag = '[|]'
                nCursorTags = preset.count(cursorTag)
                if nCursorTags > 0:
                    minPos = startwordpos
                    maxPos = self.GetCurrentPos()
                    startSelectionPos = endSelectionPos = None
                    for i in xrange(nCursorTags):
                        findpos = self.FindText(minPos, maxPos, cursorTag, stc.STC_FIND_MATCHCASE)
                        if findpos != -1:
                            self.SetSelection(findpos, findpos + len(cursorTag))
                            self.ReplaceSelection('')
                            endSelectionPos = findpos
                            if startSelectionPos is None:
                                startSelectionPos = findpos
                            minPos = findpos
                            maxPos -= len(cursorTag)
                        else:
                            break
                    if startSelectionPos is not None and endSelectionPos is not None:
                        self.SetSelection(startSelectionPos, endSelectionPos)
                        boolHighlightQuestionMarks = False
            else:
                preset = self.CreateDefaultPreset(filtername)
                self.SetSelection(startwordpos, pos)
                self.ReplaceSelection(preset)
            if boolHighlightQuestionMarks:
                minPos = self.WordEndPosition(pos,1)
                maxPos = self.GetCurrentPos()
                findpos = self.FindText(minPos, maxPos, '?')#, stc.STC_FIND_MATCHCASE)
                if findpos != -1:
                    self.SetSelection(findpos, findpos+1)
            return
        args = self.app.avsfilterdict[filtername.lower()][0]
        if not args:
            return
        if args == '()':
            self.InsertText(pos,'()')
            self.GotoPos(pos+2)
            return
        level = self.app.options['autoparentheses']
        if unichr(self.GetCharAt(pos)) == '(':
            level = 0
        if level==0:
            pass
        elif level==1:
            self.InsertText(pos,'(')
            self.GotoPos(pos+1)
        elif level==2:
            self.InsertText(pos,'()')
            self.GotoPos(pos+1)

    def UpdateCalltip(self, force=False):
        charBefore = None
        caretPos = self.GetCurrentPos()
        if caretPos > 0:
            charBefore = self.GetCharAt(caretPos - 1)
        # Cancel under certain conditions
        boolHasFocus = (self.app.FindFocus() == self)
        boolIsComment = (self.GetStyleAt(caretPos - 1) in self.commentStyle)
        if not self.app.options['calltips'] or not boolHasFocus or boolIsComment:
            self.CallTipCancelCustom()
            return
        # Determine the positions of the filter within the script
        openpos = self.GetOpenParenthesesPos(caretPos-1)
        if openpos is None:
            if force:
                openpos = self.WordEndPosition(caretPos,1) #+ 1
            else:
                self.CallTipCancelCustom()
                return
        closepos = self.BraceMatch(openpos)
        if closepos == -1:
            closepos = self.GetLength()
        # Set the force flag to true if there's an appropriate highlight
        selA, selB = self.GetSelection()
        if selA != selB:
            if selA >= openpos and selB <= closepos+1:
                force = True
            else:
                self.CallTipCancelCustom()
                return
        startwordpos = self.WordStartPosition(self.WordStartPosition(openpos, 0), 1)
        endwordpos = self.WordEndPosition(startwordpos, 1)
        # Show the calltip
        self.calltipFilter = None
        word = self.GetTextRange(startwordpos, endwordpos)
        iArgPos = None
        #~ if word.lower() in self.filterDict:
        if self.GetStyleAt(startwordpos) in self.highlightwordStyleList:
            # Show the calltip
            wordWidth = self.TextWidth(stc.STC_STYLE_DEFAULT, '%s(' % word)
            spaceWidth = self.TextWidth(stc.STC_STYLE_DEFAULT, ' ')
            spaces = ' ' * int(round(wordWidth / float(spaceWidth)))
            #~ args = self.FilterNameArgs[word.lower()]
            args = self.app.avsfilterdict[word.lower()][0]
            if args  in ('', '()'):
                self.CallTipCancelCustom()
                self.calltipFilter = word
                return
            # Get the argument index based on the cursor position
            self.cursorFilterScriptArgIndex = None
            filterMatchedArgs = self.GetFilterMatchedArgs(startwordpos, args)
            try:
                iArgPos = filterMatchedArgs[self.cursorFilterScriptArgIndex][0]
            except IndexError:
                iArgPos = None
            boolOutOfOrder = False
            if iArgPos is not None:
                currentArgName = filterMatchedArgs[self.cursorFilterScriptArgIndex][2]
                if not currentArgName:
                    for item in filterMatchedArgs[:self.cursorFilterScriptArgIndex]:
                        if item[2]:
                            boolOutOfOrder = True
                            break
            # TODO: fix iArgPos to not be None if unfinished arg...?
            # Format the calltip
            splitargs = args.split('\n\n', 1)
            tempList = []
            for iTemp, tempInfo in enumerate(self.GetFilterCalltipArgInfo(calltip=splitargs[0])):
                cArgTotal, cArgType, cArgName, boolMulti, cArgInfo = tempInfo
                s = '%s %s' % (cArgType, cArgName)
                if iTemp == iArgPos and cArgInfo and not boolOutOfOrder:
                    s += '=%s' % cArgInfo
                if boolMulti:
                    s += ' [, ...]'
                tempList.append(s)
            args0 = '(%s)' % (','.join(tempList))
            args0 = self.app.wrapFilterCalltip(args0)
            args0 = args0.replace('\n', '\n'+spaces)
            if len(splitargs) == 2:
                args = '%s\n\n%s' % (args0, splitargs[1])
            else:
                args = args0
            text = '%s%s' % (word, args)
            if self.LineFromPosition(startwordpos) == self.GetCurrentLine():
                showpos = startwordpos
            else:
                showpos = self.PositionFromLine(self.LineFromPosition(caretPos))
            xpoint, ypoint = self.PointFromPosition(showpos)
            #~ if text != self.calltiptext:
                #~ self.CallTipCancelCustom()
                #~ return
            if openpos == self.calltipOpenpos or self.flagTextChanged:
                force = True
            if self.app.options['frequentcalltips'] or force:# or (charBefore and unichr(charBefore) == '('):
                if xpoint >= 0:
                    self.CallTipShow(showpos, text)
                else:
                    xpoint = self.GetMarginWidth(0) + self.GetMarginWidth(1) + self.GetMarginWidth(2)
                    newpos = self.PositionFromPoint(wx.Point(xpoint, ypoint))
                    self.CallTipShow(newpos, text)
            self.calltiptext = text
            self.calltipFilter = word
        if self.CallTipActive():
            self.calltipOpenpos = openpos
            # BOLD THE CURRENT ARGUMENT
            a, b = 1,1
            if iArgPos is not None and not boolOutOfOrder:
                # Get the calltip arguments text positions
                try:
                    calltiptext = text
                except UnboundLocalError:
                    return
                openpos = calltiptext.find('(')
                if openpos == -1:
                    return
                argPosList = []
                startpos = openpos+1
                stoppos = startpos
                nopenSquare = 0
                argString = calltiptext[stoppos:]
                imax = len(argString)-1
                for i, c in enumerate(argString):
                    if c == '[':
                        nopenSquare += 1
                    if c == ']':
                        nopenSquare -= 1
                    if nopenSquare > 0:
                        c = 'x'
                    if c == ',' or i == imax:
                        argPosList.append((startpos, stoppos))
                        startpos = stoppos + 1
                    stoppos += 1
                if len(argPosList) == 1 and iArgPos == 1:
                    pass
                else:
                    try:
                        a, b = argPosList[iArgPos]
                    except IndexError:
                        if __debug__:
                            print>>sys.stderr, 'Error in UpdateCalltip: invalid iArgPos'
            self.CallTipSetHighlight(a,b)
        else:
            self.calltipOpenpos = None

    def CallTipCancelCustom(self):
        self.CallTipCancel()
        self.calltipFilter = None
        self.calltiptext = None
        self.calltipOpenpos = None

    def GetOpenParenthesesPos(self, pos):
        boolInside = False
        nclose = 1
        while pos >= 0:
            c = unichr(self.GetCharAt(pos))
            if self.GetStyleAt(pos) not in (self.STC_AVS_STRING, self.STC_AVS_TRIPLE, self.STC_AVS_USERSLIDER):
                if c == ')':
                    nclose += 1
                if c == '(':
                    nclose -= 1
            if nclose == 0:
                if self.GetStyleAt(pos) in self.commentStyle:
                    return None
                else:
                    return pos
            pos -= 1
        return None

    def GetFilterMatchedArgs(self, startwordpos, calltip=None):
        if calltip is None:
            filterName = self.GetTextRange(startwordpos, self.WordEndPosition(startwordpos, 1))
            calltip = self.app.avsfilterdict[filterName.lower()][0].split('\n\n')[0]
        # Get both argument lists
        filterCalltipArgInfo = self.GetFilterCalltipArgInfo(calltip=calltip)
        filterScriptArgInfo = self.GetFilterScriptArgInfo(startwordpos, calltip=calltip)
        # Determine if clip passed via "dot" operator
        isClipPrePassed = False
        try:
            firstType = filterCalltipArgInfo[0][1]
        except IndexError:
            return []
        if firstType == 'clip':
            preText = self.GetAviSynthLine(startwordpos, preSectionOnly=True)
            if preText.strip().endswith('.'):
                isClipPrePassed = True
            elif filterScriptArgInfo is not None and filterScriptArgInfo[0][1] == '?':
                isClipPrePassed = True
            else:
                lastClipIndex = 0
                for i, argInfo in enumerate(filterCalltipArgInfo):
                    if argInfo[1] != 'clip':
                        break
                    lastClipIndex = i
                try:
                    if filterScriptArgInfo is not None:
                        if filterScriptArgInfo[lastClipIndex][2] not in ('clip', 'var'):
                            isClipPrePassed = True
                    else:
                        isClipPrePassed = True
                except IndexError:
                    pass
        clipOffset = int(isClipPrePassed)
        if filterScriptArgInfo is None:
            return [(clipOffset, '', '', '')]
        # Match arguments
        calltipArgNames = [info[2].strip('"').lower() for info in filterCalltipArgInfo]
        maxCalltipIndex = len(filterCalltipArgInfo) - 1
        multiType = None
        multiIndex = None
        for index, calltipInfo in enumerate(filterCalltipArgInfo):
            cArgTotal, cArgType, cArgName, cBoolMulti, cArgInfo = calltipInfo
            if cBoolMulti:
                multiType = cArgType
                multiIndex = index
                postMultiIndex = index
                # TODO: handle multiple multiTypes...
                break
        filterArgInfo = []
        for scriptArgIndex, argInfo in enumerate(filterScriptArgInfo):
            argname, argvalue, argtype = argInfo
            if argname:
                # Check named arguments
                try:
                    calltipIndex = calltipArgNames.index(argname.lower())
                except ValueError:
                    calltipIndex = None
            else:
                calltipIndex = scriptArgIndex + clipOffset
                # Check for multi-arg possibility
                if multiIndex is not None and calltipIndex > multiIndex:
                    if argtype in (multiType, 'var'):
                        calltipIndex = multiIndex
                    else:
                        multiType = None
                        postMultiIndex += 1
                        calltipIndex = postMultiIndex
                if calltipIndex > maxCalltipIndex:
                    calltipIndex = None
                    continue
            if calltipIndex is not None:
                calltipFilterInfo = filterCalltipArgInfo[calltipIndex][0]
            else:
                calltipFilterInfo = ''
            filterArgInfo.append((calltipIndex, calltipFilterInfo, argname, argvalue))
        return filterArgInfo

    def GetFilterScriptArgInfo(self, startwordpos, calltip=None):
        openpos = self.FindText(startwordpos, self.GetTextLength(), '(')
        if openpos == -1:
            self.cursorFilterScriptArgIndex = 0
            return None
        # Grab the text line from the script
        line = self.LineFromPosition(openpos)
        posStart = openpos - self.PositionFromLine(line)
        iArg = 0
        pos1 = openpos
        posEnd = None
        while pos1 < self.GetLength():
            if unichr(self.GetCharAt(pos1)) == '(':
                posEnd = self.BraceMatch(pos1)
                if posEnd == -1:
                    posEnd = self.GetLineEndPosition(line) #self.GetLength()
                pos1 += 1
                break
            pos1 += 1
        if posEnd is None:
            self.cursorFilterScriptArgIndex = 0
            return None
        if pos1 == posEnd:
            self.cursorFilterScriptArgIndex = 0
            return None #[('','','')]
        currentPos = self.GetCurrentPos()
        currentIndex = None
        argsList = []
        counter = 0
        pos2 = self.GetNextValidCommaPos(pos1, allowparentheses=False)
        while pos2 is not None and pos2 <= posEnd:
            txt = self.GetTextRange(pos1,pos2).strip()
            argsList.append(txt)
            if pos2 >= currentPos and currentIndex is None:
                currentIndex = counter
            counter += 1
            pos1 = pos2 + 1
            pos2 = self.GetNextValidCommaPos(pos1, allowparentheses=False)
        if currentIndex is None:
            currentIndex = counter
        txt = self.GetTextRange(pos1,posEnd).strip()
        argsList.append(txt)
        argInfo = []
        for txt in argsList:
            try:
                argname, argvalue = [s.strip() for s in txt.split('=', 1)]
                argname = argname.strip(string.whitespace+'\\')
                argvalue = argvalue.strip(string.whitespace+'\\')
                argtype = 'named'
            except ValueError:
                argname = u''
                argvalue = txt
                argname = argname.strip(string.whitespace+'\\')
                argvalue = argvalue.strip(string.whitespace+'\\')
                argtype = self.GetAviSynthVarType(argvalue)
            #~ argname = argname.strip(string.whitespace+'\\')
            #~ argvalue = argvalue.strip(string.whitespace+'\\')
            argInfo.append((argname, argvalue, argtype))
        self.cursorFilterScriptArgIndex = currentIndex
        return argInfo

    def GetFilterCalltipArgInfo(self, word=None, calltip=None):
        if calltip is None:
            # Get the user slider info from the filter's calltip
            calltip = self.app.avsfilterdict[word.lower()][0].split('\n\n')[0]
        # Get rid of any commas in square brackets
        calltip = re.sub(r'\[.*\]', '[...]', calltip)
        # Split the arguments by commas
        if calltip.startswith('(') and calltip.endswith(')'):
            calltip = calltip[1:-1]
        elif calltip.startswith('('):
            calltip = calltip[1:]
        elif calltip.endswith(')'):
            calltip = calltip[:-1]
        #~ return [s.strip() for s in calltip.split(',')]
        argInfo = []
        for item in calltip.split(','):
            item = item.strip()
            if not item.strip():
                continue
            if item.count('[...]') > 0:
                boolMulti = True
                item = item.replace('[...]', '')
            else:
                boolMulti = False
            try:
                argtype, nameAndInfo = [s.strip() for s in item.split(' ', 1)]
                try:
                    name, info = [s.strip() for s in nameAndInfo.split('=', 1)]
                except ValueError:
                    name = nameAndInfo
                    info = u''
                argInfo.append((item, argtype.lower(), name, boolMulti, info))
            except ValueError:
                if item.lower() in ('clip', 'int', 'float', 'bool', 'string'):
                    argInfo.append((item, item.lower(), u'', boolMulti, u''))
                else:
                    # Assume it's a clip
                    argInfo.append((item, u'clip', item, boolMulti, u''))
        return argInfo

    def CreateDefaultPreset(self, filtername, calltip=None):
        if calltip is None:
            calltip = self.app.avsfilterdict[filtername.lower()][0].split('\n\n')[0]
        if calltip == '':
            return filtername
        argList = []
        for i, info in enumerate(self.GetFilterCalltipArgInfo(filtername, calltip)):
            totalInfo, cArgType, cArgName, boolRepeatArg, cArgInfo = info
            argtype, argname, guitype, defaultValue, other = self.app.ParseCalltipArgInfo(totalInfo)
            namedarg = ''
            if cArgName.startswith('"') and cArgName.endswith('"'):
                namedarg = cArgName.strip('"')+'='
            #~ if defaultValue is not None:
            if defaultValue or defaultValue == 0:
                if guitype == 'color':
                    argList.append('%s$%s' % (namedarg, defaultValue))
                elif argtype in ('float', 'int') and other is not None:
                    nDecimal = other[2]
                    strTemplate = '%.'+str(nDecimal)+'f'
                    try:
                        argList.append(namedarg+strTemplate % defaultValue)
                    except (TypeError, ValueError):
                        defaultValue = re.sub(r'\bclip\b', 'last', str(defaultValue), re.IGNORECASE)
                        argList.append(namedarg+defaultValue)
                else:
                    argList.append(namedarg+str(defaultValue))#.lower())
            elif argtype == 'clip' and i == 0:
                pass   # argList.append('last')
            else:
                argList.append(namedarg+'?')
        return '%s(%s)' % (filtername, ', '.join(argList))

    def GetAviSynthLine(self, pos, preSectionOnly=False, postSectionOnly=False):
        '''Returns the line of text at pos, accommodating for AviSynth line continuations'''
        linenumber = self.LineFromPosition(pos)
        if preSectionOnly:
            lines = [self.GetLine(linenumber)[:pos-self.PositionFromLine(linenumber)]]
        elif postSectionOnly:
            lines = [self.GetLine(linenumber)[pos-self.PositionFromLine(linenumber):]]
        else:
            lines = [self.GetLine(linenumber)]
        if not postSectionOnly:
            iLine = linenumber - 1
            while iLine >= 0:
                linetxt = self.GetLine(iLine)
                if lines[0].strip().startswith('\\') or linetxt.strip().endswith('\\'):
                    lines.insert(0, linetxt)
                else:
                    break
                iLine -= 1
        if not preSectionOnly:
            maxlinenumber = self.GetLineCount() - 1
            iLine = linenumber + 1
            while iLine <= maxlinenumber:
                linetxt = self.GetLine(iLine)
                if lines[-1].strip().endswith('\\') or linetxt.strip().startswith('\\'):
                    lines.append(linetxt)
                else:
                    break
                iLine += 1
        return ' '.join([s.strip().strip('\\') for s in lines])

    def GetAviSynthVarType(self, strVar):
        strVar = strVar.strip()
        if not strVar:
            return 'empty'
        # Check int
        if strVar.isdigit():
            return 'int'
        # Check float
        try:
            float(strVar)
            return 'float'
        except ValueError:
            pass
        # Check hex number
        if strVar.startswith('$'):
            return 'hex'
        # Check boolean
        if strVar.lower() in ('true', 'false'):
            return 'bool'
        # Check string
        if strVar.startswith('"') and strVar.endswith('"'):
            return 'string'
        if strVar.startswith('"'):
            # Incomplete string...
            return 'string'
        # Check if it's a named argument
        if strVar.count('=') > 0:
            return 'named'
        # Check if it's the Avisynth variable last
        if strVar.lower() == 'last':
            return 'clip'
        # Heuristic...
        if strVar.count('.') > 0:
            name = strVar.split('.')[-1].split('(')[0].lower()
            if name in ('width', 'height', 'framecount'):
                return 'int'
            elif name in ('framerate',):
                return 'float'
            elif name.startswith('is'):
                return 'bool'
        # If none of the above, it's a variable name
        if self.AVI is not None:
            vartype = self.AVI.GetVarType(strVar)
            if vartype in ('int', 'float', 'string', 'bool'):
                return vartype
        return 'var'

    def GetNextValidCommaPos(self, pos, checkChar=',', allowparentheses=False):
        #~ txt = self.GetTextRange(pos, self.GetLength())
        #~ newPos = pos
        #~ for c in txt:
            #~ if c == ',':
                #~ if self.GetStyleAt(newPos) not in (self.STC_AVS_STRING, self.STC_AVS_TRIPLE, self.STC_AVS_USERSLIDER):
                    #~ return newPos
            #~ newPos += 1
        nOpen = 0
        while pos <= self.GetLength():
            c = unichr(self.GetCharAt(pos))
            if c == '(' and not allowparentheses:
                pos = self.BraceMatch(pos)
                if pos == wx.NOT_FOUND:
                    return None
                continue
            if c == checkChar:
                if self.GetStyleAt(pos) not in (self.STC_AVS_STRING, self.STC_AVS_TRIPLE, self.STC_AVS_USERSLIDER, self.STC_AVS_COMMENT):
                    return pos
            pos += 1
        return None

    def ShowFilterDocumentation(self, name=None):
        if name is None:
            name = self.calltipFilter
        #~ if not name.lower() in self.app.avsfilterdict:
            #~ return True
        docsearchpaths = []
        avisynthdir = self.app.options['avisynthdir']
        docsearchpathstring = self.app.options['docsearchpaths']
        for path in docsearchpathstring.split(';'):
            path = path.strip()
            if path == '':
                continue
            if path.rstrip('\\') == '%avisynthdir%':
                docsearchpaths.append(avisynthdir)
            elif path.startswith('%avisynthdir%\\'):
                path = os.path.join(avisynthdir, path.split('%avisynthdir%\\')[1])
                if os.path.isdir(path):
                    docsearchpaths.append(path)
            else:
                if os.path.isdir(path):
                    docsearchpaths.append(path)
        extensions = ['.htm', '.html', '.txt', '.lnk']
        for dir in docsearchpaths:
            filenames = []
            for filename in os.listdir(dir):
                base, ext = os.path.splitext(filename)
                if ext in extensions:
                    if re.findall(r'(\b|[_\W]|readme)%s(\b|[_\W]|readme)' % name, base, re.IGNORECASE):
                        filenames.append((extensions.index(ext), filename))
            if filenames:
                filenames.sort()
                filename = os.path.join(dir, filenames[0][1])
                os.startfile(filename)
                return True
        url = self.app.options['docsearchurl'].replace('%filtername%', name.replace('_', '+'))
        os.startfile(url)
        return False

    def GetFilterNameAtCursor(self, pos=None):
        if self.calltipFilter is not None:
            word = self.calltipFilter
        else:
            if pos is None:
                pos = self.GetCurrentPos()
            posA = self.WordStartPosition(pos, 1)
            posB = self.WordEndPosition(pos, 1)
            word = self.GetTextRange(posA, posB)
            #~ if word.lower() in self.filterDict:
                #~ self.ShowFilterDocumentation(word)
            #~ else:
                #~ self.ShowFilterDocumentation(self.GetSelectedText())
        return word

    # Event functions
    @staticmethod
    def OnFindPressed(event):
        #~ if wx.VERSION > (2, 9) and hasattr(event, 'GetEventObject'):
            #~ event = event.GetEventObject().GetData()
        if hasattr(event, 'GetEventObject'):
            nb = event.GetEventObject().GetParent()
            self = nb.GetPage(nb.GetSelection())
        else:
            self = event
            event = self.finddata
        dlgflags = event.GetFlags()
        text = event.GetFindString()
        stcflags = 0
        if wx.FR_MATCHCASE & dlgflags:
            stcflags = stcflags|stc.STC_FIND_MATCHCASE
        if wx.FR_WHOLEWORD & dlgflags:
            stcflags = stcflags|stc.STC_FIND_WHOLEWORD
        if wx.FR_DOWN & dlgflags:
            minPos = self.GetCurrentPos()
            maxPos = self.GetLineEndPosition(self.GetLineCount()-1)
            findpos = self.FindText(minPos,maxPos,text,stcflags)
            if findpos==-1:
                findpos = self.FindText(0,maxPos,text,stcflags)
            if findpos==-1:
                dlg = wx.MessageDialog(self, _('Cannot find "%(text)s".') % locals(), _('Information'),wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()
                dlg.Destroy()
            else:
                self.SetSelection(findpos, findpos+len(text))
        else:
            minPos = self.GetSelectionStart()-1
            maxPos = 0
            findpos = self.FindText(minPos,maxPos,text,stcflags)
            if findpos==-1:
                minPos = self.GetLineEndPosition(self.GetLineCount()-1)
                findpos = self.FindText(minPos,maxPos,text,stcflags)
            if findpos==-1:
                dlg = wx.MessageDialog(self, _('Cannot find "%(text)s".') % locals(), _('Information'),wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()
                dlg.Destroy()
            else:
                self.SetAnchor(findpos)
                self.SetCurrentPos(findpos+len(text))
        return findpos
        
    @staticmethod
    def OnReplacePressed(event):
        #~ if wx.VERSION > (2, 9) and hasattr(event, 'GetEventObject'):
            #~ event = event.GetEventObject().GetData()
        nb = event.GetEventObject().GetParent()
        self = nb.GetPage(nb.GetSelection())
        if self.GetSelectedText() == event.GetFindString():
            self.ReplaceSelection(event.GetReplaceString())
            self.OnFindPressed(event)
        else:
            self.OnFindPressed(event)

    @staticmethod
    def OnReplaceAllPressed(event):
        #~ if wx.VERSION > (2, 9) and hasattr(event, 'GetEventObject'):
            #~ event = event.GetEventObject().GetData()
        nb = event.GetEventObject().GetParent()
        self = nb.GetPage(nb.GetSelection())
        self.GotoPos(0)
        exitflag = 0
        count = 0
        while exitflag!=1:
            dlgflags = event.GetFlags()
            text = event.GetFindString()
            stcflags = 0
            if wx.FR_MATCHCASE&dlgflags:   stcflags = stcflags|stc.STC_FIND_MATCHCASE
            if wx.FR_WHOLEWORD&dlgflags:   stcflags = stcflags|stc.STC_FIND_WHOLEWORD
            minPos = self.GetCurrentPos()
            maxPos = self.GetLineEndPosition(self.GetLineCount()-1)
            findpos = self.FindText(minPos,maxPos,text,stcflags)
            if findpos!=-1:
                self.SetAnchor(findpos)
                self.SetCurrentPos(findpos+len(text))
                replacetext = event.GetReplaceString()
                self.ReplaceSelection(replacetext)
                self.SetAnchor(self.GetCurrentPos()-len(replacetext))
                count = count+1
            else:
                exitflag = 1
        self.GotoPos(0)
        dlg = wx.MessageDialog(self, _('Replaced %(count)i times') % locals(),_('Replace Information'),wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    @staticmethod
    def OnFindNext(self):
        if self.finddata.GetFindString()=='':
            self.ShowFindDialog()
        else:
            self.OnFindPressed(self)

    @staticmethod
    def OnFindClose(event):
        AvsStyledTextCtrl.frdlg.Destroy()
        del AvsStyledTextCtrl.frdlg

    def OnUpdateUI(self, event):
        # Get the character before the caret
        charBefore = None
        caretPos = self.GetCurrentPos()
        if caretPos > 0:
            charBefore = self.GetCharAt(caretPos - 1)
        # Syntax highlighting
        if self.app.options['syntaxhighlight']:
            # Highlight braces
            braceAtCaret = -1
            braceOpposite = -1
            # check before
            if charBefore and unichr(charBefore) in "[]{}()":# and styleBefore == stc.STC_P_OPERATOR:
                braceAtCaret = caretPos - 1
            # check after
            if braceAtCaret < 0:
                charAfter = self.GetCharAt(caretPos)
                #~ styleAfter = self.GetStyleAt(caretPos)
                if charAfter and unichr(charAfter) in "[]{}()":# and styleAfter == stc.STC_P_OPERATOR:
                    braceAtCaret = caretPos
            if braceAtCaret >= 0:
                braceOpposite = self.BraceMatch(braceAtCaret)
            #~ if braceAtCaret != -1:
            if braceOpposite == -1:
                self.BraceBadLight(braceAtCaret)
            else:
                self.BraceHighlight(braceAtCaret, braceOpposite)
            #~ if self.commentStyle in (self.GetStyleAt(braceAtCaret), self.GetStyleAt(braceAtCaret)):
            if self.GetStyleAt(braceAtCaret) in self.nonBraceStyles or self.GetStyleAt(braceOpposite) in self.nonBraceStyles:
                self.BraceHighlight(-1, -1)
        # Display call tips
        self.UpdateCalltip()
        self.flagTextChanged = False
        
        # incompatible, STC_UPDATEUI event doesn't tigger on wx2.9
        self.CodeFolding()
    
    def CodeFolding(self):    # update folding level
        lineCount = self.GetLineCount()
        line = 0
        while line < lineCount:
            if self.GetFoldLevel(line) & stc.STC_FOLDLEVELHEADERFLAG:
                hasBrace = False
                hasBlock = False
                for pos in range(self.PositionFromLine(line), self.GetLineEndPosition(line)+1):
                    if unichr(self.GetCharAt(pos)) == '{' and self.GetStyleAt(pos) == self.STC_AVS_OPERATOR:
                        hasBrace = True
                        break
                if not hasBrace:
                    for pos in range(self.GetLineEndPosition(line), self.PositionFromLine(line)-1, -1):
                        if self.GetStyleAt(pos) == self.STC_AVS_BLOCKCOMMENT and self.GetStyleAt(pos-1) != self.STC_AVS_BLOCKCOMMENT:
                            hasBlock = True
                            break
                if hasBrace:
                    posMatch = self.BraceMatch(pos)
                    if posMatch != stc.STC_INVALID_POSITION:
                        lineEnd = self.LineFromPosition(posMatch) + 1
                        lastChild = self.GetLastChild(line, -1) + 1                        
                        if line+1 == lineEnd:
                            if not self.GetFoldExpanded(line):
                                self.SetFoldExpanded(line, True)
                                self.Expand(line, True)
                            self.SetFoldLevel(line, self.GetFoldLevel(line) & stc.STC_FOLDLEVELNUMBERMASK)
                    else:
                        lineEnd = lastChild = lineCount                        
                    level = (self.GetFoldLevel(line) & stc.STC_FOLDLEVELNUMBERMASK) + 1
                    for lineNum in range(line+1, lineEnd):
                        self.SetFoldLevel(lineNum, self.GetFoldLevel(lineNum) & 0xF000 | level)
                    for lineNum in range(lineEnd, lastChild):
                        self.SetFoldLevel(lineNum, self.GetFoldLevel(lineNum)-1)
                elif hasBlock:
                    end = pos
                    while self.GetStyleAt(end+1) == self.STC_AVS_BLOCKCOMMENT:
                        end += 1
                    lineEnd = self.LineFromPosition(end) + 1
                    lastChild = self.GetLastChild(line, -1) + 1 
                    if line+1 == lineEnd:
                        if not self.GetFoldExpanded(line):
                            self.SetFoldExpanded(line, True)
                            self.Expand(line, True)
                        self.SetFoldLevel(line, self.GetFoldLevel(line) & stc.STC_FOLDLEVELNUMBERMASK)
                    else:
                        for lineNum in range(line+1, self.LineFromPosition(end)+1):
                            if self.GetFoldLevel(lineNum) & stc.STC_FOLDLEVELHEADERFLAG and not self.GetFoldExpanded(lineNum):
                                self.SetFoldExpanded(lineNum, True)
                                self.Expand(lineNum, True)
                        level = (self.GetFoldLevel(line) & stc.STC_FOLDLEVELNUMBERMASK) + 1
                        for lineNum in range(line+1, lineEnd):
                            self.SetFoldLevel(lineNum, self.GetFoldLevel(lineNum) & 0xF000 | level)
                        for lineNum in range(lineEnd, lastChild):
                            self.SetFoldLevel(lineNum, self.GetFoldLevel(lineNum)-1)
                elif self.GetStyleAt(self.PositionFromLine(line)) != self.STC_AVS_ENDCOMMENT and self.GetStyleAt(self.PositionFromLine(line+1)) == self.STC_AVS_ENDCOMMENT:
                    for lineNum in range(line+1, lineCount):
                        if self.GetFoldLevel(lineNum) & stc.STC_FOLDLEVELHEADERFLAG and not self.GetFoldExpanded(lineNum):
                            self.SetFoldExpanded(lineNum, True)
                            self.Expand(lineNum, True)                    
                        level = (self.GetFoldLevel(line) & stc.STC_FOLDLEVELNUMBERMASK) + 1
                    for lineNum in range(line+1, lineCount):                        
                        self.SetFoldLevel(lineNum, self.GetFoldLevel(lineNum) & 0xF000 | level)
                else:
                    if not self.GetFoldExpanded(line):
                        self.SetFoldExpanded(line, True)
                        self.Expand(line, True)
                    #~ else:
                        #~ lineNext = line + 1
                    for lineNum in range(line+1, self.GetLastChild(line, -1)+1):
                        self.SetFoldLevel(lineNum, self.GetFoldLevel(lineNum)-1)
                    self.SetFoldLevel(line, self.GetFoldLevel(line)&stc.STC_FOLDLEVELNUMBERMASK)
                    #~ line = lineNext - 1
            line += 1

    def OnTextChange(self, event):
        self.fitNumberMarginWidth()
        #~ self.UpdateCalltip(force=True)
        self.flagTextChanged = True
    
    def OnTextCharAdded(self, event):
        if unichr(event.GetKey()) == '\n':
            line = self.GetCurrentLine() - 1
            indentText = self.GetTextRange(self.PositionFromLine(line), self.GetLineIndentPosition(line))
            self.AddText(indentText)
            level = self.GetFoldLevel(line)
            if level & stc.STC_FOLDLEVELHEADERFLAG:
                self.SetFoldLevel(line + 1, level & stc.STC_FOLDLEVELNUMBERMASK)

    def OnNeedShown(self, event):
        line = self.LineFromPosition(event.GetPosition())
        lineEnd = self.LineFromPosition(event.GetPosition()+event.GetLength())
        while line < lineEnd:
            level = self.GetFoldLevel(line)
            if level & stc.STC_FOLDLEVELHEADERFLAG and not self.GetFoldExpanded(line):
                self.SetFoldExpanded(line, True)
                self.Expand(line, True)
            line += 1

    def OnKeyUp(self, event):
        pos = self.GetCurrentPos()
        #~ charCurrent = self.GetCharAt(pos-1)
        #~ charBefore = self.GetCharAt(pos-2)
        #~ charAfter= self.GetCharAt(pos)
        #~ isCurrentCap = unichr(charCurrent).isalpha() and unichr(charCurrent).isupper()#unichr(charCurrent).isalpha() and event.ShiftDown() #
        #~ isBeforeBlank = unichr(charBefore).isspace() or unichr(charBefore)=='.' or charBefore==0
        #~ isBeforeBlank = unichr(charBefore).isspace() or unichr(charBefore) in self.app.avsoperators or charBefore==0
        #~ isAfterBlank = unichr(charAfter).isspace() or unichr(charAfter)=='.' or charAfter==0
        #~ validChar = isCurrentCap and isBeforeBlank and isAfterBlank
        #~ isCommentStyle = self.commentStyle == self.GetStyleAt(pos - 1)
        #~ if self.app.options['autocomplete'] and validChar and not(self.AutoCompActive()) and not isCommentStyle:
            #~ keywords = self.app.avsazdict.get(unichr(charCurrent).lower(), [])[:]
            #~ for i in range(len(keywords)-1, -1, -1):
                #~ if keywords[i] in self.app.options['autocompleteexclusions']:
                    #~ del keywords[i]
            #~ if keywords:
                #~ self.AutoCompShow(1, ' '.join(keywords))
        keys = (wx.WXK_ESCAPE, wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_TAB)
        if event.GetKeyCode() not in keys\
        and not self.AutoCompActive()\
        and not (self.CallTipActive() and self.app.options['calltipsoverautocomplete'])\
        and self.GetStyleAt(pos-1) not in self.nonBraceStyles:
            start = self.WordStartPosition(pos,1)
            end = self.WordEndPosition(pos,1)
            char = unichr(self.GetCharAt(start))
            if pos == end:
                if self.app.options['autocomplete']\
                and (char.isalpha() and char.isupper() or char == '_')\
                and pos - start == self.app.options['autocompletelength']:
                    wx.CallAfter(self.ShowAutocomplete, auto=1)
                elif self.app.options['autocompletesingle'] and char.isalpha():
                    wx.CallAfter(self.ShowAutocomplete, auto=2)
        event.Skip()

    def OnKeyDown(self,event):
        key = event.GetKeyCode()
        #~ flags = event.GetModifiers()
        if self.AutoCompActive() and key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER, wx.WXK_TAB) and not (event.ControlDown() or event.AltDown() or event.ShiftDown()):
            self.FinishAutocomplete(key=key)
            #~ if key == wx.WXK_TAB:
                #~ self.app.tab_processed = True
        #~ elif key == wx.WXK_TAB and mod == wx.MOD_NONE:
            #~ self.app.OnMenuEditIndentSelection()
        #~ elif key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and not event.ControlDown():
            #~ pos = self.GetCurrentPos()
            #~ line = self.LineFromPosition(pos)
            #~ indentText = self.GetTextRange(self.PositionFromLine(line), self.GetLineIndentPosition(line))
            #~ self.ReplaceSelection('\n'+indentText)
            #~ level = self.GetFoldLevel(line)
            #~ if level & stc.STC_FOLDLEVELHEADERFLAG:
                #~ self.SetFoldLevel(line+1, level & stc.STC_FOLDLEVELNUMBERMASK)
        else:
            event.Skip()
        
    def OnMiddleDown(self,event):
        xypos = event.GetPosition()
        self.GotoPos(self.PositionFromPoint(xypos))

    def OnMouseMotion(self,event):
        if event.MiddleIsDown():
            self.OnMiddleDown(event)
        elif event.LeftIsDown():
            xypos = event.GetPosition()
            self.SetCurrentPos(self.PositionFromPoint(xypos))
        #~ else:
            #~ pass

    def OnLeftMouseDown(self, event):
        #~ self.CallTipCancelCustom()
        event.Skip()

    def OnCalltipClick(self, event):
        if wx.GetKeyState(wx.WXK_ALT) or wx.GetKeyState(wx.WXK_CONTROL) or wx.GetKeyState(wx.WXK_SHIFT):
            self.ShowFilterDocumentation()
        else:
            self.CallTipCancelCustom()

    def OnKillFocus(self, event):
        self.CallTipCancelCustom()
        self.AutoCompCancel()
        event.Skip()

    def OnSetFocus(self, event):
        self.UpdateCalltip()
        event.Skip()

    def OnStyleNeeded(self, event, forceAll=False):
        if forceAll:
            start = -1
            end = self.GetLength()
        else:
            pos = self.GetEndStyled()
            line = self.LineFromPosition(pos)
            start = self.PositionFromLine(line) - 1
            while line > 0 and self.GetStyleAt(start) == self.STC_AVS_BLOCKCOMMENT:
                line -= 1
                start = self.PositionFromLine(line) - 1
            end = event.GetPosition()
        if start < 1:
            start = 0
            state = self.STC_AVS_DEFAULT
        else:
            state = self.GetStyleAt(start)
            if state == self.STC_AVS_STRINGEOL:
                start += 1
                state = self.STC_AVS_DEFAULT
        isCommentC = isCommentNest = isLoadPlugin = False
        self.endstyled = pos = start
        fragment = []
        hexfragment = []
        self.StartStyling(pos, 31)
        while pos <= end:
            ch = unichr(self.GetCharAt(pos))
            isEOD = (ch == unichr(0))
            isEOL = (ch == '\n' or ch == '\r' or isEOD)
            if state == self.STC_AVS_DEFAULT:
                if ch == '#':
                    state = self.STC_AVS_COMMENT
                elif ch == '/' and unichr(self.GetCharAt(pos+1)) == '*':
                    end = self.GetTextLength()
                    pos += 1
                    isCommentC = True
                    state = self.STC_AVS_BLOCKCOMMENT
                    line = self.LineFromPosition(pos)
                    self.SetFoldLevel(line, self.GetFoldLevel(line) | stc.STC_FOLDLEVELHEADERFLAG)
                elif ch == '"':
                    self.ColourTo(pos-1, state)
                    if unichr(self.GetCharAt(pos+1)) == '"' and unichr(self.GetCharAt(pos+2)) == '"':
                        pos += 2
                        state = self.STC_AVS_TRIPLE                        
                    else:
                        state = self.STC_AVS_STRING
                    if isLoadPlugin:
                        isLoadPlugin = pos
                elif ch == '$':
                    hexfragment = []
                    state = self.STC_AVS_NUMBERBAD
                elif ch == '[' and unichr(self.GetCharAt(pos+1)) == '*':
                    end = self.GetTextLength()
                    pos += 1
                    isCommentNest = 1
                    state = self.STC_AVS_BLOCKCOMMENT
                    line = self.LineFromPosition(pos)
                    self.SetFoldLevel(line, self.GetFoldLevel(line) | stc.STC_FOLDLEVELHEADERFLAG)
                elif ch == '[' and unichr(self.GetCharAt(pos+1)) == '<':
                    pos += 1
                    state = self.STC_AVS_USERSLIDER
                elif ch.isalpha() or ch == '_' or ch in self.app.avssingleletters:
                    fragment = [ch]
                    state = self.STC_AVS_IDENTIFIER
                elif ch.isdigit():
                    state = self.STC_AVS_NUMBER
                elif ch in self.app.avsoperators:
                    self.ColourTo(pos - 1, state)
                    self.ColourTo(pos, self.STC_AVS_OPERATOR)
                    if ch == '{':
                        line = self.LineFromPosition(pos)
                        self.SetFoldLevel(line, self.GetFoldLevel(line) | stc.STC_FOLDLEVELHEADERFLAG)
                else:
                    if isEOD:
                        self.ColourTo(pos - 1, self.STC_AVS_DEFAULT)
                    else:
                        self.ColourTo(pos, self.STC_AVS_DEFAULT)
            elif state == self.STC_AVS_COMMENT:
                if isEOL:
                    if isEOD:
                        self.ColourTo(pos - 1, self.STC_AVS_COMMENT)
                    else:
                        self.ColourTo(pos, self.STC_AVS_COMMENT)
                    state = self.STC_AVS_DEFAULT
            elif state == self.STC_AVS_BLOCKCOMMENT:
                if isEOD:
                    self.ColourTo(pos - 1, self.STC_AVS_BLOCKCOMMENT)
                elif isCommentC:
                    if ch == '*' and unichr(self.GetCharAt(pos+1)) == '/':
                        pos += 1
                        self.ColourTo(pos, self.STC_AVS_BLOCKCOMMENT)
                        isCommentC = False
                        state = self.STC_AVS_DEFAULT
                elif isCommentNest:
                    if ch == '*' and unichr(self.GetCharAt(pos+1)) == ']':
                        pos += 1
                        isCommentNest -= 1
                        if not isCommentNest:
                            self.ColourTo(pos, self.STC_AVS_BLOCKCOMMENT)
                            state = self.STC_AVS_DEFAULT
                    elif ch == '[' and unichr(self.GetCharAt(pos+1)) == '*':
                        pos += 1
                        isCommentNest += 1
            elif state == self.STC_AVS_IDENTIFIER:
                if fragment[0] not in self.app.avssingleletters and (ch.isalnum() or ch == '_'):
                    fragment.append(ch)
                else:
                    pos -= 1
                    word =''.join(fragment).lower()
                    if word in self.app.avsdatatypes and unichr(self.GetCharAt(pos+1)).isspace():
                        self.ColourTo(pos, self.STC_AVS_DATATYPE)
                    elif word in self.app.avsfilterdict:
                        #~ self.ColourTo(pos, self.keywordstyles[word])
                        self.ColourTo(pos, self.app.avsfilterdict[word][1])
                        if word == 'loadplugin':
                            isLoadPlugin = True
                    elif word in self.app.avskeywords:
                        self.ColourTo(pos, self.STC_AVS_KEYWORD)
                    elif word in self.app.avsmiscwords:
                        self.ColourTo(pos, self.STC_AVS_MISCWORD)
                        if word == '__end__':
                            line = self.LineFromPosition(pos)
                            self.SetFoldLevel(line, self.GetFoldLevel(line) | stc.STC_FOLDLEVELHEADERFLAG)
                            pos = self.GetLength()
                            self.ColourTo(pos, self.STC_AVS_ENDCOMMENT)
                    else:
                        self.ColourTo(pos, self.STC_AVS_DEFAULT)
                    fragment = []
                    state = self.STC_AVS_DEFAULT
            elif state == self.STC_AVS_STRING:
                if self.app.options['usestringeol']:
                    if unichr(self.GetCharAt(pos-1)) == '"' and unichr(self.GetCharAt(pos)) == '"' and unichr(self.GetCharAt(pos+1)) == '"':
                        state = self.STC_AVS_TRIPLE
                        pos += 1
                    elif ch == '"' or isEOL:
                        if isEOL:
                            if isEOD:
                                self.ColourTo(pos - 1, self.STC_AVS_STRINGEOL)                                
                            else:
                                self.ColourTo(pos, self.STC_AVS_STRINGEOL)
                            isLoadPlugin = False
                        else:
                            self.ColourTo(pos, self.STC_AVS_STRING)
                            if isLoadPlugin:
                                self.parseDllname(isLoadPlugin, pos)
                                isLoadPlugin = False
                        state = self.STC_AVS_DEFAULT
                else:
                    if unichr(self.GetCharAt(pos-1)) == '"' and unichr(self.GetCharAt(pos)) == '"' and unichr(self.GetCharAt(pos+1)) == '"':
                        state = self.STC_AVS_TRIPLE
                        pos += 1
                    elif ch == '"':
                        self.ColourTo(pos, self.STC_AVS_STRING)                        
                        state = self.STC_AVS_DEFAULT
                        if isLoadPlugin:
                            self.parseDllname(isLoadPlugin, pos)
                            isLoadPlugin = False
                    elif isEOD:
                        self.ColourTo(pos - 1, self.STC_AVS_STRING)
                        state = self.STC_AVS_DEFAULT
                        isLoadPlugin = False
            elif state == self.STC_AVS_TRIPLE:
                if isEOD or (ch == '"' and unichr(self.GetCharAt(pos-1)) == '"' and unichr(self.GetCharAt(pos-2)) == '"'):
                    self.ColourTo(pos, self.STC_AVS_TRIPLE)
                    state = self.STC_AVS_DEFAULT
                    if isLoadPlugin:
                        if not isEOD:
                            self.parseDllname(isLoadPlugin, pos)
                        isLoadPlugin = False
            elif state == self.STC_AVS_NUMBER:
                if not ch.isdigit():
                    pos -= 1
                    self.ColourTo(pos, self.STC_AVS_NUMBER)
                    state = self.STC_AVS_DEFAULT
            elif state == self.STC_AVS_NUMBERBAD:
                if ch.isalnum() or ch == '_':
                    hexfragment.append(ch)
                else:
                    pos -= 1
                    #~ if len(hexfragment) == 6 and sum([c.isdigit() or c.lower() in ('a', 'b', 'c', 'd', 'e', 'f') for c in hexfragment]) == 6:
                        #~ self.ColourTo(pos, self.STC_AVS_NUMBER)
                    #~ else:
                        #~ self.ColourTo(pos, self.STC_AVS_NUMBERBAD)
                    try:
                        int(''.join(hexfragment), 16)
                        self.ColourTo(pos, self.STC_AVS_NUMBER)
                    except:
                        self.ColourTo(pos, self.STC_AVS_NUMBERBAD)
                    hexfragment = []
                    state = self.STC_AVS_DEFAULT
            elif state == self.STC_AVS_USERSLIDER:
                if isEOL or (ch == ']' and unichr(self.GetCharAt(pos-1)) == '>'):
                    if isEOL:
                        self.ColourTo(pos, self.STC_AVS_NUMBERBAD)
                    else:
                        self.ColourTo(pos, self.STC_AVS_USERSLIDER)
                    state = self.STC_AVS_DEFAULT
            pos += 1
            if pos > end and state in (self.STC_AVS_STRING, self.STC_AVS_TRIPLE):
                if end+1 <= self.GetTextLength():
                    end += 1
                    
    def ColourTo(self, pos, style):
        self.SetStyling(pos +1 - self.endstyled, style)
        self.endstyled = pos+1
        
    def parseDllname(self, start, end):
        path = self.GetTextRange(start, end).lower().strip('"')
        #~ print path
        if path.endswith('.dll'):
            dllname = os.path.basename(path[:-4])
            if dllname.count('_') and dllname not in self.app.dllnameunderscored:
                self.app.dllnameunderscored.add(dllname)
                self.app.defineScriptFilterInfo()

    def OnMarginClick(self, evt):
        # fold and unfold as needed
        if evt.GetMargin() == 2:
            if evt.GetShift() and evt.GetControl():
                self.FoldAll()
            else:
                lineClicked = self.LineFromPosition(evt.GetPosition())

                if self.GetFoldLevel(lineClicked) & stc.STC_FOLDLEVELHEADERFLAG:
                    if evt.GetShift():
                        self.SetFoldExpanded(lineClicked, True)
                        self.Expand(lineClicked, True, True, 1)
                    elif evt.GetControl():
                        if self.GetFoldExpanded(lineClicked):
                            self.SetFoldExpanded(lineClicked, False)
                            self.Expand(lineClicked, False, True, 0)
                        else:
                            self.SetFoldExpanded(lineClicked, True)
                            self.Expand(lineClicked, True, True, 100)
                    else:
                        self.ToggleFold(lineClicked)

    def FoldAll(self):
        if self.GetEndStyled() != self.GetLength():
            self.OnStyleNeeded(None, forceAll=True)
            self.CodeFolding()
        lineCount = self.GetLineCount()
        expanding = True

        # find out if we are folding or unfolding
        for lineNum in range(lineCount):
            if self.GetFoldLevel(lineNum) & stc.STC_FOLDLEVELHEADERFLAG:
                expanding = not self.GetFoldExpanded(lineNum)
                break

        lineNum = 0

        while lineNum < lineCount:
            level = self.GetFoldLevel(lineNum)
            if level & stc.STC_FOLDLEVELHEADERFLAG and \
               (level & stc.STC_FOLDLEVELNUMBERMASK) == stc.STC_FOLDLEVELBASE:

                if expanding:
                    self.SetFoldExpanded(lineNum, True)
                    lineNum = self.Expand(lineNum, True)
                    lineNum = lineNum - 1
                else:
                    lastChild = self.GetLastChild(lineNum, -1)
                    self.SetFoldExpanded(lineNum, False)

                    if lastChild > lineNum:
                        self.HideLines(lineNum+1, lastChild)

            lineNum = lineNum + 1

    def Expand(self, line, doExpand, force=False, visLevels=0, level=-1):
        lastChild = self.GetLastChild(line, level)
        line = line + 1

        while line <= lastChild:
            if force:
                if visLevels > 0:
                    self.ShowLines(line, line)
                else:
                    self.HideLines(line, line)
            else:
                if doExpand:
                    self.ShowLines(line, line)

            if level == -1:
                level = self.GetFoldLevel(line)

            if level & stc.STC_FOLDLEVELHEADERFLAG:
                if force:
                    if visLevels > 1:
                        self.SetFoldExpanded(line, True)
                    else:
                        self.SetFoldExpanded(line, False)

                    line = self.Expand(line, doExpand, force, visLevels-1)

                else:
                    if doExpand and self.GetFoldExpanded(line):
                        line = self.Expand(line, True, force, visLevels-1)
                    else:
                        line = self.Expand(line, False, force, visLevels-1)
            else:
                line = line + 1

        return line

# Dialog for choosing AviSynth specific fonts and colors
class AvsStyleDialog(wx.Dialog):
    # TODO: add export and import styles, macros to import...
    def __init__(self, parent, dlgInfo, options, extra, title=_('AviSynth fonts and colors')):
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title)
        self.options = options.copy()
        # Create the font buttons
        self.controls = {}
        self.controls2 = {}
        self.notebook = wx.Notebook(self, wx.ID_ANY, style=wx.NO_BORDER)
        def OnNotebookPageChanged(event):
            event.GetEventObject().GetCurrentPage().SetFocus()
            event.Skip()
        for tabLabel, tabInfo in dlgInfo:
            tabPanel = wx.Panel(self.notebook, wx.ID_ANY)
            self.notebook.AddPage(tabPanel, tabLabel)
            sizer = wx.FlexGridSizer(cols=4, hgap=20, vgap=5)
            sizer.Add((0,0), 0)
            for label in ( _('Font'), _('Text color'), _('Background')):
                staticText = wx.StaticText(tabPanel, wx.ID_ANY, label)
                font = staticText.GetFont()
                font.SetUnderlined(True)
                font.SetWeight(wx.FONTWEIGHT_BOLD)
                staticText.SetFont(font)
                sizer.Add(staticText, flag=wx.ALIGN_CENTER)
            for label, key in tabInfo:
                (fontSize, fontStyle, fontWeight, fontUnderline,
                fontFace, fontFore, fontBack) = self.ParseStyleInfo(options[key].split(','))                
                if fontFace is not None:
                    font = wx.Font(fontSize, wx.FONTFAMILY_DEFAULT, fontStyle, fontWeight, fontUnderline, faceName=fontFace)
                else:
                    font = None
                # Create the controls
                if type(label) is tuple:
                    label, optKey, tip = label
                    staticText = checkbox = wx.CheckBox(tabPanel, wx.ID_ANY, label)
                    checkbox.SetValue(parent.options[optKey])
                    checkbox.SetToolTipString(tip)
                    self.controls2[optKey] = checkbox
                else:
                    staticText = wx.StaticText(tabPanel, wx.ID_ANY, label)
                if font is not None:
                    fontLabel = '%s, %d' % (fontFace, fontSize)
                    fontButton = wxButtons.GenButton(tabPanel, wx.ID_ANY, label=fontLabel)
                    fontButton.SetUseFocusIndicator(False)
                    fontButton.SetFont(font)
                    self.Bind(wx.EVT_BUTTON, self.OnButtonFont, fontButton)
                else:
                    fontButton = None
                if fontFore is not None:
                    #~ foreButton = wx.StaticText(tabPanel, wx.ID_ANY, size=(50, 20))
                    #~ foreButton.SetBackgroundColour(wx.Colour(*fontFore))
                    #~ foreButton.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
                    #~ foreButton.Bind(wx.EVT_LEFT_UP, self.OnButtonColor)
                    foreButton = colourselect.ColourSelect(tabPanel, wx.ID_ANY, colour=wx.Colour(*fontFore), size=(50,23))
                else:
                    foreButton = None
                if fontBack is not None:
                    #~ backButton = wx.StaticText(tabPanel, wx.ID_ANY, size=(50, 20))
                    #~ backButton.SetBackgroundColour(wx.Colour(*fontBack))
                    #~ backButton.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
                    #~ backButton.Bind(wx.EVT_LEFT_UP, self.OnButtonColor)
                    backButton = colourselect.ColourSelect(tabPanel, wx.ID_ANY, colour=wx.Colour(*fontBack), size=(50,23))
                else:
                    backButton = None
                sizer.Add(staticText, flag=wx.ALIGN_CENTER)
                if fontButton is not None:
                    sizer.Add(fontButton, flag=wx.ALIGN_CENTER)
                else:
                    sizer.Add((0,0), flag=wx.ALIGN_CENTER)
                if foreButton is not None:
                    sizer.Add(foreButton, flag=wx.ALIGN_CENTER)
                else:
                    sizer.Add((0,0), flag=wx.ALIGN_CENTER)
                if backButton is not None:
                    sizer.Add(backButton, flag=wx.ALIGN_CENTER)
                else:
                    sizer.Add((0,0), flag=wx.ALIGN_CENTER)
                self.controls[key] = (fontButton, foreButton, backButton)
            tabSizer = wx.BoxSizer(wx.VERTICAL)
            tabSizer.Add(sizer, 0, wx.ALL, 10)
            tabPanel.SetSizerAndFit(tabSizer)
        self.notebook.SetSelection(0)
        # Miscellaneous options
        label, optKey, tip = extra
        checkbox = wx.CheckBox(self, wx.ID_ANY, label)
        checkbox.SetValue(parent.options[optKey])
        checkbox.SetToolTipString(tip)
        self.controls2[optKey] = checkbox
        # Standard buttons
        okay  = wx.Button(self, wx.ID_OK, _('OK'))
        self.Bind(wx.EVT_BUTTON, self.OnButtonOK, okay)
        cancel = wx.Button(self, wx.ID_CANCEL, _('Cancel'))
        btns = wx.StdDialogButtonSizer()
        btns.Add(checkbox)
        btns.AddButton(okay)
        btns.AddButton(cancel)
        btns.Realize()
        # Size the elements
        dlgSizer = wx.BoxSizer(wx.VERTICAL)
        #~ dlgSizer.Add(sizer, 0, wx.EXPAND|wx.ALL, 5)
        dlgSizer.Add(self.notebook, 0, wx.EXPAND|wx.ALL, 5)
        dlgSizer.Add(btns, 0, wx.EXPAND|wx.ALL, 10)
        self.SetSizer(dlgSizer)
        dlgSizer.Fit(self)
        self.sizer = dlgSizer
        # Misc
        okay.SetDefault()
        self.Centre(wx.CENTRE_ON_SCREEN)
        
    @staticmethod
    def ParseStyleInfo(styleInfo):
        # Get the style info (face, size, bold/italic/underline, color, background)
        (fontSize, fontStyle, fontWeight, fontUnderline,
        fontFace, fontFore, fontBack) = (10, wx.FONTSTYLE_NORMAL,
        wx.FONTWEIGHT_NORMAL, False, None, None, None)
        for info in styleInfo:
            infolower = info.lower().strip()
            if infolower.startswith('face:'):
                fontFace = info[5:]
            elif infolower.startswith('size:'):
                fontSize = int(info[5:])
            elif infolower.startswith('fore:'):
                color = info.split(':')[1].strip().lstrip('#')
                r = int(color[0:2], 16)
                g = int(color[2:4], 16)
                b = int(color[4:6], 16)
                fontFore = (r, g, b)
            elif infolower.startswith('back:'):
                color = info.split(':')[1].strip().lstrip('#')
                r = int(color[0:2], 16)
                g = int(color[2:4], 16)
                b = int(color[4:6], 16)
                fontBack = (r, g, b)
            elif infolower =='bold':
                fontWeight = wx.FONTWEIGHT_BOLD
            elif infolower =='italic':
                fontStyle = wx.FONTSTYLE_ITALIC
            elif infolower =='underline':
                fontUnderline = True
        return (fontSize, fontStyle, fontWeight, fontUnderline,
                fontFace, fontFore, fontBack)
                
    def OnButtonOK(self, event):
        if self.UpdateDict():
            event.Skip()

    def OnButtonFont(self, event):
        button = event.GetEventObject()
        font = button.GetFont()
        # Show the font dialog
        data = wx.FontData()
        data.EnableEffects(False)
        data.SetInitialFont(font)
        dlg = wx.FontDialog(self, data)
        if dlg.ShowModal() == wx.ID_OK:
            data = dlg.GetFontData()
            font = data.GetChosenFont()
            fontFace = font.GetFaceName()
            fontSize = font.GetPointSize()
            fontLabel = '%s, %d' % (fontFace, fontSize)
            button.SetLabel(fontLabel)
        button.SetFont(font)
        button.SetBestSize()
        button.Refresh()
        self.sizer.Fit(self)
        dlg.Destroy()

    def GetDict(self):
        return self.options
        
    def GetDict2(self):
        for key in self.controls2:
            self.controls2[key] = self.controls2[key].GetValue()
        return self.controls2

    def UpdateDict(self):
        for key, value in self.controls.items():
            styleList = []
            fontButton, foreButton, backButton = value
            if fontButton is not None:
                font = fontButton.GetFont()
                styleList.append('face:%s' % font.GetFaceName())
                styleList.append('size:%i' % font.GetPointSize())
            if foreButton is not None:
                #~ styleList.append('fore:#%02x%02x%02x' % foreButton.GetBackgroundColour().Get())
                styleList.append('fore:#%02x%02x%02x' % foreButton.GetColour().Get())
            if backButton is not None:
                #~ styleList.append('back:#%02x%02x%02x' % backButton.GetBackgroundColour().Get())
                styleList.append('back:#%02x%02x%02x' % backButton.GetColour().Get())
            if fontButton is not None:
                if font.GetWeight() == wx.FONTWEIGHT_BOLD:
                    styleList.append('bold')
                if font.GetStyle() == wx.FONTSTYLE_ITALIC:
                    styleList.append('italic')
                if font.GetUnderlined():
                    styleList.append('underlined')
            stylestring = ','.join(styleList)
            self.options[key] = stylestring
        return True

# Dialog for scrap window
class ScrapWindow(wx.Dialog):
    def __init__(self, parent, title=_('Scrap Window'), pos=wx.DefaultPosition, size=(250,250)):
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title, pos, size, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.parent = parent
        # Create the stc control
        self.textCtrl = self.createTextCtrl()        
        self.textCtrl.nInserted = 0
        # Define keyboard shortcuts
        #~ self.BindShortcuts()
        # Add the text from the previous session
        txt, anchor, pos = self.parent.options['scraptext']
        self.textCtrl.SetText(txt)
        self.textCtrl.SetAnchor(anchor)
        self.textCtrl.SetCurrentPos(pos)
        self.textCtrl.EnsureCaretVisible()
        self.textCtrl.EmptyUndoBuffer()
        # Set the width for the horizontal scrollbar
        maxWidth = 50
        for line in txt.split('\n'):
            width = self.textCtrl.TextWidth(stc.STC_STYLE_DEFAULT, line)
            if width > maxWidth:
                maxWidth = width
        self.textCtrl.SetScrollWidth(maxWidth)
        # Event binding
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        # Misc
        sizer = wx.BoxSizer()
        sizer.Add(self.textCtrl, 1, wx.EXPAND)
        self.SetSizerAndFit(sizer)
        self.neverShown = True

    def createTextCtrl(self):
        textCtrl = stc.StyledTextCtrl(self, wx.ID_ANY, size=(250,250), style=wx.SIMPLE_BORDER)
        # Define the default style
        textCtrl.StyleSetSpec(stc.STC_STYLE_DEFAULT, self.parent.options['textstyles']['scrapwindow'])
        textCtrl.StyleClearAll()
        # Set a style to use for text flashing upon insertion
        textCtrl.StyleSetSpec(stc.STC_P_WORD, "fore:#FF0000,bold")
        # Define the context menu
        textCtrl.UsePopUp(0)
        self.idInsertFrame = wx.NewId()
        self.idGetStatusText = wx.NewId()
        self.idToggleScrapWindow = wx.NewId()
        menuInfo = (
            (_('Undo')+'\tCtrl+Z', lambda event: textCtrl.Undo(), wx.ID_ANY),
            (_('Redo')+'\tCtrl+Y', lambda event: textCtrl.Redo(), wx.ID_ANY),
            (''),
            (_('Cut')+'\tCtrl+X', lambda event: textCtrl.Cut(), wx.ID_ANY),
            (_('Copy')+'\tCtrl+C', lambda event: textCtrl.Copy(), wx.ID_ANY),
            (_('Paste')+'\tCtrl+V', lambda event: textCtrl.Paste(), wx.ID_ANY),
            (''),
            (_('Select all')+'\tCtrl+A', lambda event: textCtrl.SelectAll(), wx.ID_ANY),
            (''),
            (_('Refresh'), self.OnRefresh, wx.ID_ANY),
            (_('Insert frame #'), self.OnInsertFrameNumber, self.idInsertFrame),
            (_('Save to file...'), self.OnSave, wx.ID_SAVE),
            (_('Clear all'), self.OnClearAll, wx.ID_ANY),
            (_('Toggle scrap window'), self.OnToggleScrapWindow, self.idToggleScrapWindow),
        )
        self.contextMenu = menu = wx.Menu()
        for eachMenuInfo in menuInfo:
            # Define optional arguments
            if not eachMenuInfo:
                menu.AppendSeparator()
            else:
                label = eachMenuInfo[0]
                handler = eachMenuInfo[1]
                status = ''
                id = eachMenuInfo[2]
                menuItem = menu.Append(id, label, status)
                textCtrl.Bind(wx.EVT_MENU, handler, menuItem)
        textCtrl.contextMenu = menu
        textCtrl.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)
        # Misc properties
        textCtrl.SetMarginWidth(1, 0)
        textCtrl.SetEOLMode(stc.STC_EOL_LF)
        return textCtrl

    def BindShortcuts(self):
        menuInfo = (
            (_('Insert frame #'), self.idInsertFrame),
            (_('Save script'), wx.ID_SAVE),
            (_('Toggle scrap window'), self.idToggleScrapWindow),
        )
        menu = self.contextMenu
        counter = 0
        accList = []
        for itemName, shortcut, id in self.parent.options['shortcuts']:
            for label, id in menuInfo:
                if itemName.endswith(label):
                    counter += 1
                    accel = wx.GetAccelFromString('\t'+shortcut)
                    if accel:
                        accList.append((accel.GetFlags(), accel.GetKeyCode(), id))
                    menuItem = menu.FindItemById(id)
                    label = '%s\t%s' % (menuItem.GetItemLabelText(), shortcut)
                    menuItem.SetItemLabel(label)
                    break
            if counter == len(menuInfo):
                break
        accTable = wx.AcceleratorTable(accList)
        self.textCtrl.SetAcceleratorTable(accTable)

    def OnClose(self, event):
        self.Hide()

    def OnContextMenu(self, event):
        win = event.GetEventObject()
        pos = win.ScreenToClient(event.GetPosition())
        try:
            win.PopupMenu(win.contextMenu, pos)
        except AttributeError:
            print>>sys.stderr, _('Error: no contextMenu variable defined for window')

    def OnRefresh(self, event):
        scrap = self.textCtrl
        scrap.StartStyling(0, 31)
        scrap.SetStyling(scrap.GetTextLength(), stc.STC_STYLE_DEFAULT)
        self.Refresh()

    def OnInsertFrameNumber(self, event):
        frame = self.parent.GetFrameNumber()
        self.textCtrl.ReplaceSelection(str(frame))

    def OnSave(self, event):
        filefilter = _('Text document (*.txt)|*.txt|All files (*.*)|*.*')
        initialdir = self.parent.options['recentdir']
        dlg = wx.FileDialog(self,_('Save scrap text'),
            initialdir, '', filefilter, wx.SAVE | wx.OVERWRITE_PROMPT)
        ID = dlg.ShowModal()
        if ID == wx.ID_OK:
            filename = dlg.GetPath()
            self.textCtrl.SaveFile(filename)
            self.parent.options['recentdir'] = os.path.dirname(filename)
        dlg.Destroy()

    def OnClearAll(self, event):
        self.textCtrl.ClearAll()

    def OnToggleScrapWindow(self, event):
        self.Hide()

    def GetText(self):
        return self.textCtrl.GetText()

    def SetText(self, txt):
        return self.textCtrl.SetText(txt)

    def Show(self):
        if self.neverShown:
            xp, yp = self.parent.GetPositionTuple()
            wp, hp = self.parent.GetSizeTuple()
            wd, hd = wx.ScreenDC().GetSizeTuple()
            ws, hs = self.GetSizeTuple()
            self.SetPosition((min(xp+wp-50, wd-ws),-1))
        super(ScrapWindow, self).Show()
        if self.neverShown:
            self.Refresh()
            self.neverShown = False

    def write(self, msg):
        self.parent.MacroWriteToScrap(msg)

# Dialog and validator for defining user slider
class UserSliderValidator(wx.PyValidator):
    def __init__(self, ctrlDict, labels):
        wx.PyValidator.__init__(self)
        self.ctrlDict = ctrlDict
        self.labels = labels

    def Clone(self):
        return UserSliderValidator(self.ctrlDict, self.labels)

    def Validate(self, parent):
        textCtrl = self.GetWindow()
        text = textCtrl.GetValue()
        if len(text) == 0:
            self.ShowWarning(textCtrl, _('This field must contain a value!'))
            return False
        elif textCtrl == self.ctrlDict['label']:
            try:
                temp  = str(text)
            except UnicodeEncodeError:
                temp = text
            if temp in self.labels:
                self.ShowWarning(textCtrl, _('This slider label already exists!'))
                return False
            if self.getModFromLabel(text) == -1:
                self.ShowWarning(textCtrl, _('Invalid slider label modulo syntax!'))
                return False
            return True
        else:
            try:
                float(text)
            except ValueError:
                self.ShowWarning(textCtrl, _('This field must contain a number!'))
                return False
            try:
                minValue = float(self.ctrlDict['min'].GetValue())
                maxValue = float(self.ctrlDict['max'].GetValue())
                value = float(self.ctrlDict['val'].GetValue())
                # Validate ranges
                if minValue >= maxValue and textCtrl == self.ctrlDict['min']:
                    self.ShowWarning(textCtrl, _('The min value must be less than the max!'))
                    return False
                if value < minValue or value > maxValue and textCtrl == self.ctrlDict['val']:
                    self.ShowWarning(textCtrl, _('The initial value must be between the min and the max!'))
                    return False
                # Validate modulo divisibility
                mod = self.getModFromLabel(self.ctrlDict['label'].GetValue())
                if mod == -1:
                    self.ShowWarning(textCtrl, _('Invalid slider label modulo syntax!'))
                    return False
                if mod is not None:
                    if int(minValue) % mod != 0 and textCtrl == self.ctrlDict['min']:
                        self.ShowWarning(textCtrl, _('The min value must be a multiple of %(mod)s!') % locals())
                        return False
                    if int(maxValue) % mod != 0 and textCtrl == self.ctrlDict['max']:
                        self.ShowWarning(textCtrl, _('The max value must be a multiple of %(mod)s!') % locals())
                        return False
                    if int(value) % mod != 0 and textCtrl == self.ctrlDict['val']:
                        self.ShowWarning(textCtrl, _('The initial value must be a multiple of %(mod)s!') % locals())
                        return False
                    if mod > (maxValue - minValue):
                        self.ShowWarning(self.ctrlDict['min'], _('The difference between the min and max must be greater than %(mod)s!') % locals())
                        return False
            except ValueError:
                pass
            return True

    def getModFromLabel(self, label):
        mod = None
        label = self.ctrlDict['label'].GetValue()
        splitlabel = label.split('%', 1)
        if len(splitlabel) == 2:
            try:
                mod = int(splitlabel[1])
                if mod <= 0:
                    mod = -1
            except ValueError:
                mod = -1
        return mod

    def ShowWarning(self, textCtrl, message):
        color = textCtrl.GetBackgroundColour()
        textCtrl.SetBackgroundColour('pink')
        textCtrl.Refresh()
        wx.MessageBox(message, _('Error'), style=wx.OK|wx.ICON_ERROR)
        textCtrl.SetBackgroundColour(color)
        textCtrl.SetSelection(-1,-1)
        textCtrl.SetFocus()
        textCtrl.Refresh()

    def TransferToWindow(self):
        return True

    def TransferFromWindow(self):
        return True

class UserSliderDialog(wx.Dialog):
    def __init__(self, parent, labels, initialValueText=''):
        wx.Dialog.__init__(self, None, wx.ID_ANY, _('Define user slider'))
        self.parent = parent
        # Entry fields
        gridSizer = wx.FlexGridSizer(cols=2, hgap=10, vgap=5)
        gridSizer.AddGrowableCol(1)
        self.ctrlDict = {}
        for eachKey, eachLabel in self.fieldInfo():
            textCtrl = wx.TextCtrl(self, validator=UserSliderValidator(self.ctrlDict, labels))
            staticText = wx.StaticText(self, wx.ID_ANY, eachLabel)
            gridSizer.Add(staticText, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
            gridSizer.Add(textCtrl, 0, wx.EXPAND)
            self.ctrlDict[eachKey] = textCtrl
        if initialValueText:
            self.ctrlDict['val'].SetValue(initialValueText)
        # Standard buttons
        okay  = wx.Button(self, wx.ID_OK, _('OK'))
        okay.SetDefault()
        cancel = wx.Button(self, wx.ID_CANCEL, _('Cancel'))
        btns = wx.StdDialogButtonSizer()
        btns.AddButton(okay)
        btns.AddButton(cancel)
        btns.Realize()
        # Set the sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(gridSizer, 0, wx.EXPAND|wx.ALL, 20)
        sizer.Add(btns, 0, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(sizer)
        sizer.Fit(self)

    def fieldInfo(self):
        return (
            ('label', _('Slider label:')),
            ('min', _('Min value:')),
            ('max', _('Max value:')),
            ('val', _('Initial value:')),
        )

    def GetSliderText(self):
        textDict = dict([(k, v.GetValue()) for k,v in self.ctrlDict.items()])
        textDict['open'] = self.parent.sliderOpenString
        textDict['close'] = self.parent.sliderCloseString
        return '%(open)s"%(label)s", %(min)s, %(max)s, %(val)s%(close)s' % textDict

# Dialog for AviSynth filter information
class AvsFunctionDialog(wx.Dialog):
    def __init__(self, parent, filterDict, overrideDict, presetDict, removedSet, autcompletetypeFlags, installedFilternames, functionName=None, CreateDefaultPreset=None, ExportFilterData=None):
        wx.Dialog.__init__(
            self, parent, wx.ID_ANY,
            _('Add or override AviSynth functions in the database'),
            size=(500, 300), style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER
        )
        self.filterDict = filterDict.copy()
        self.overrideDict = overrideDict.copy()
        self.presetDict = presetDict.copy()
        self.removedSet = removedSet
        self.autcompletetypeFlags = autcompletetypeFlags
        self.installedFilternames = installedFilternames
        self.CreateDefaultPreset = CreateDefaultPreset
        self.ExportFilterData = ExportFilterData
        self.CreateWindowElements()
        self.CreateFilterInfoDialog()
        wx.FutureCall(100, self.HighlightFunction, functionName)

    def HighlightFunction(self, functionName):
        # Highlight the function if specified
        if functionName is not None:
            lowername = functionName.lower()
            for index in xrange(self.notebook.GetPageCount()):
                panel = self.notebook.GetPage(index)
                listbox = panel.listbox
                for i in xrange(listbox.GetCount()):
                    label = listbox.GetString(i)
                    if label.split()[0].lower() == lowername:
                        self.notebook.SetSelection(index)
                        listbox.SetSelection(i)
                        self.EditFunctionInfo()
                        return
            # functionName was not found, show dialog to define new function
            self.AddNewFunction(functionName)

    def CreateWindowElements(self):
        self.notebook = wx.Notebook(self, wx.ID_ANY, style=wx.NO_BORDER)
        pageInfo = (
            (_('Core filters'), 0),
            (_('Plugins'), 2),
            (_('User functions'), 3),
            (_('Script functions'), 4),
            (_('Clip properties'), 1),
        )
        for title, index in pageInfo:
            panel = wx.Panel(self.notebook, wx.ID_ANY, size=(700,-1))
            self.notebook.AddPage(panel, title)
            # List box

            #~ choices = [
                #~ self.overrideDict.get(key, value)[0]
                #~ for key, value in self.filterDict.items()
                #~ if value[2] == index
            #~ ]

            #~ d1 = dict([(lowername, name) for lowername, (name,args,ftype) in self.filterDict.items() if ftype==index])
            #~ d2 = dict([(lowername, name+' *') for lowername, (name,args,ftype) in self.overrideDict.items() if ftype==index])
            #~ d1.update(d2)
            #~ choices = [value for key, value in d1.items()]

            choices = []
            keys = set(self.filterDict.keys()+self.overrideDict.keys()+self.presetDict.keys())
            for key in keys:
                extra = ' '
                name, args, ftype = self.overrideDict.get(key, (None, None, None))
                if name is None:
                    try:
                        name, args, ftype = self.filterDict[key]
                    except:
                        del self.presetDict[key]
                        continue
                else:
                    extra += '*'
                if key in self.presetDict:
                    extra += '~'
                if ftype == index:
                    choices.append(name+extra)

            listbox = wx.CheckListBox(panel, wx.ID_ANY, choices=choices, size=(-1,300), style=wx.LB_SORT)
            if choices:
                listbox.SetSelection(0)
            listbox.Bind(wx.EVT_LISTBOX_DCLICK, lambda event: self.EditFunctionInfo())
            for i in xrange(listbox.GetCount()):
                name = listbox.GetString(i).split()[0]
                if name.lower() not in self.removedSet:
                    listbox.Check(i)
            title = title.lower()
            autocompletecheckbox = wx.CheckBox(panel, wx.ID_ANY, _('Include %(title)s in autcompletion lists') % locals())
            autocompletecheckbox.SetValue(self.autcompletetypeFlags[index])
            # Buttons
            buttonadd = wx.Button(panel, wx.ID_ANY, _('New function'))#, size=(100, -1))
            buttonedit = wx.Button(panel, wx.ID_ANY, _('Edit selected'))
            buttondelete = wx.Button(panel, wx.ID_ANY, _('Delete selected'))
            buttoncheckall = wx.Button(panel, wx.ID_ANY, _('Select all'))
            buttonuncheckall = wx.Button(panel, wx.ID_ANY, _('Clear all'))
            panel.Bind(wx.EVT_BUTTON, lambda event: self.AddNewFunction(ftype=-1), buttonadd)
            panel.Bind(wx.EVT_BUTTON, lambda event: self.EditFunctionInfo(), buttonedit)
            panel.Bind(wx.EVT_BUTTON, lambda event: self.DeleteFunction(), buttondelete)
            panel.Bind(wx.EVT_BUTTON, lambda event: self.CheckAllFunctions(True), buttoncheckall)
            panel.Bind(wx.EVT_BUTTON, lambda event: self.CheckAllFunctions(False), buttonuncheckall)
            buttonSizer = wx.BoxSizer(wx.VERTICAL)
            buttonSizer.Add(buttonadd, 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)
            buttonSizer.Add(buttonedit, 0, wx.EXPAND|wx.BOTTOM, 5)
            buttonSizer.Add(buttondelete, 0, wx.EXPAND|wx.BOTTOM, 5)
            buttonSizer.Add(wx.StaticLine(panel, wx.ID_ANY, style=wx.HORIZONTAL), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)
            buttonSizer.Add(buttonuncheckall, 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)
            buttonSizer.Add(buttoncheckall, 0, wx.EXPAND|wx.BOTTOM, 5)
            #~ if index == 2:
                #~ self.buttonclearlongnames = wx.Button(panel, wx.ID_ANY, _('Clear long names'))
                #~ panel.Bind(wx.EVT_BUTTON, lambda event: self.ClearLongNames(), self.buttonclearlongnames)
                #~ buttonSizer.Add(self.buttonclearlongnames, 0, wx.EXPAND|wx.BOTTOM, 5)
            if index == 2:
                buttonselectinstalled = wx.Button(panel, wx.ID_ANY, _('Select installed'))
                panel.Bind(wx.EVT_BUTTON, lambda event: self.SelectInstalledFilters(), buttonselectinstalled)
                buttonSizer.Add(buttonselectinstalled, 0, wx.EXPAND|wx.BOTTOM, 5)
                
            # Size the elements in the panel
            listboxSizer = wx.BoxSizer(wx.HORIZONTAL)
            listboxSizer.Add(listbox, 1, wx.EXPAND|wx.RIGHT, 15)            
            listboxSizer.Add(buttonSizer, 0, wx.EXPAND|wx.RIGHT, 5)            
            panelSizer = wx.BoxSizer(wx.VERTICAL)
            panelSizer.Add(listboxSizer, 1, wx.EXPAND|wx.ALL, 5)            
            panelSizer.Add(autocompletecheckbox, 0, wx.ALL, 5)
            panelSizer.Add((-1, 5))
            panel.SetSizer(panelSizer)
            panelSizer.Layout()
            # Bind items to the panel itself
            panel.listbox = listbox
            panel.autocompletecheckbox = autocompletecheckbox
            panel.functiontype = index
        # Buttons
        button0 = wx.Button(self, wx.ID_ANY, _('Import from files'))
        self.Bind(wx.EVT_BUTTON, lambda event: self.ImportFromFiles(), button0)
        button1 = wx.Button(self, wx.ID_ANY, _('Export customizations'))
        self.Bind(wx.EVT_BUTTON, lambda event: self.ExportCustomizations(), button1)
        button2 = wx.Button(self, wx.ID_ANY, _('Clear customizations'))
        self.Bind(wx.EVT_BUTTON, lambda event: self.ClearCustomizations(), button2)
        button3 = wx.Button(self, wx.ID_ANY, _('Clear manual presets'))
        self.Bind(wx.EVT_BUTTON, lambda event: self.ClearPresets(), button3)
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(button0, 0, wx.RIGHT, 5)
        buttonSizer.Add(button1, 0, wx.RIGHT, 5)
        buttonSizer.Add(button2, 0, wx.RIGHT, 5)
        buttonSizer.Add(button3, 0, wx.RIGHT, 5)        
        self.checkBox = wx.CheckBox(self, wx.ID_ANY, _("When importing, don't show the choice dialog"))
        # Standard buttons
        okay  = wx.Button(self, wx.ID_OK, _('OK'))
        #~ self.Bind(wx.EVT_BUTTON, self.OnButtonOK, okay)
        cancel = wx.Button(self, wx.ID_CANCEL, _('Cancel'))
        sdtbtns = wx.StdDialogButtonSizer()
        sdtbtns.Add(self.checkBox)
        sdtbtns.AddButton(okay)
        sdtbtns.AddButton(cancel)
        sdtbtns.Realize()
        # Size the elements
        dlgSizer = wx.BoxSizer(wx.VERTICAL)
        dlgSizer.Add(self.notebook, 1, wx.EXPAND|wx.ALL, 5)
        dlgSizer.Add(buttonSizer, 0, wx.LEFT, 5)
        dlgSizer.Add(wx.StaticLine(self, style=wx.HORIZONTAL), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)
        dlgSizer.Add(sdtbtns, 0, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(dlgSizer)
        dlgSizer.SetSizeHints(self)
        dlgSizer.Layout()
        # Misc
        def OnPageChanged(event):
            event.GetEventObject().GetCurrentPage().SetFocus()
            event.Skip()
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, OnPageChanged)
        self.notebook.GetCurrentPage().listbox.SetFocus()
        okay.SetDefault()

    def CreateFilterInfoDialog(self, resetargsbutton=True):
        dlg = wx.Dialog(self, wx.ID_ANY, _('Edit function information'))
        staticText0 = wx.StaticText(dlg, wx.ID_ANY, _('Name:'))
        textCtrl0 = wx.TextCtrl(dlg, wx.ID_ANY, size=(200,-1))
        staticText1 = wx.StaticText(dlg, wx.ID_ANY, _('Type:'))
        choices = [_('core filter'), _('clip property'), _('plugin'), _('user function'), _('script function')]
        choiceBox1 = wx.Choice(dlg, wx.ID_ANY, choices=choices)
        staticText2 = wx.StaticText(dlg, wx.ID_ANY, _('Arguments:'))
        staticText2_4 = wx.StaticText(dlg, wx.ID_ANY, _('define sliders'))
        staticText2_5 = wx.StaticText(dlg, wx.ID_ANY, _('reset to default'))
        for eachCtrl in (staticText2_4, staticText2_5):
            font = eachCtrl.GetFont()
            font.SetUnderlined(True)
            eachCtrl.SetFont(font)
            eachCtrl.SetForegroundColour(wx.Colour(0,0,255))
            eachCtrl.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        def OnArgsEditSliders(event):
            name = textCtrl0.GetValue()
            dlg2 = AvsFilterAutoSliderInfo(dlg, self.GetParent(), name, textCtrl2.GetValue(), title=_('Slider information'))
            ID = dlg2.ShowModal()
            if ID == wx.ID_OK:
                textCtrl2.SetValue(dlg2.GetNewFilterInfo())
            dlg2.Destroy()
        staticText2_4.Bind(wx.EVT_LEFT_DOWN, OnArgsEditSliders)
        def OnClickSetToDefault(event):
            textCtrl0.SetValue(dlg.defaultName)
            textCtrl2.SetValue(dlg.defaultArgs)
        staticText2_5.Bind(wx.EVT_LEFT_DOWN, OnClickSetToDefault)
        textCtrl2 = wx.TextCtrl(dlg, wx.ID_ANY, size=(200,200), style=wx.TE_MULTILINE|wx.HSCROLL)
        def OnArgsChange(event):
            if checkBox3.IsChecked():
                name = textCtrl0.GetValue() #dlg.defaultName
                args= textCtrl2.GetValue()
                textCtrl3.SetValue(self.CreateDefaultPreset(name, args))
        textCtrl0.Bind(wx.EVT_TEXT, OnArgsChange)
        textCtrl2.Bind(wx.EVT_TEXT, OnArgsChange)
        #~ textCtrl2.Bind(wx.EVT_LEFT_DCLICK, OnArgsEditSliders)
        staticText3 = wx.StaticText(dlg, wx.ID_ANY, _('Preset:'))
        checkBox3 = wx.CheckBox(dlg, wx.ID_ANY, _('Auto-generate'))
        def OnCheck(event):
            if checkBox3.IsChecked():
                textCtrl3.SetEditable(False)
                colour = self.GetBackgroundColour()
                textCtrl3.SetBackgroundColour(colour)
                OnArgsChange(None)
            else:
                textCtrl3.SetEditable(True)
                textCtrl3.SetBackgroundColour(wx.WHITE)
        checkBox3.Bind(wx.EVT_CHECKBOX, OnCheck)
        textCtrl3 = wx.TextCtrl(dlg, wx.ID_ANY, size=(-1,50), style=wx.TE_MULTILINE|wx.HSCROLL)
        # Standard buttons
        okay  = wx.Button(dlg, wx.ID_OK, _('OK'))
        def OnFilterInfoDialogButtonOK(event):
            newName = textCtrl0.GetValue()
            enteredName = dlg.enteredName
            if enteredName is None:
                lowername = newName.lower()
                if lowername in self.overrideDict or lowername in self.filterDict:
                    wx.MessageBox(_('Filter name already exists!'), _('Error'), style=wx.OK|wx.ICON_ERROR)
                    textCtrl0.SetFocus()
                    return
                if not newName or newName[0].isdigit() or re.findall('\W', newName):
                    wx.MessageBox(_('Invalid filter name!'), _('Error'), style=wx.OK|wx.ICON_ERROR)
                    textCtrl0.SetFocus()
                    return
            elif newName.lower() != enteredName.lower():
                wx.MessageBox(_('Renaming not allowed!'), _('Error'), style=wx.OK|wx.ICON_ERROR)
                textCtrl0.SetFocus()
                return
            if dlg.typeBox.GetCurrentSelection() == 2 and newName.count('_') == 0:
                wx.MessageBox(_('You must use dllname_function naming format for plugins!'), 
                              _('Error'), style=wx.OK|wx.ICON_ERROR)
                textCtrl0.SetFocus()
                return
            event.Skip()
        dlg.Bind(wx.EVT_BUTTON, OnFilterInfoDialogButtonOK, okay)
        cancel = wx.Button(dlg, wx.ID_CANCEL, _('Cancel'))
        btns = wx.StdDialogButtonSizer()
        btns.AddButton(okay)
        btns.AddButton(cancel)
        btns.Realize()
        # Size the elements
        sizer01 = wx.FlexGridSizer(cols=4, hgap=5, vgap=5)
        sizer01.Add(staticText0, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer01.Add(textCtrl0, 0, wx.EXPAND|wx.RIGHT, 10)
        sizer01.Add(staticText1, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer01.Add(choiceBox1, 0, wx.EXPAND)
        sizer2 = wx.BoxSizer(wx.HORIZONTAL)
        sizer2.Add(staticText2, 0, wx.ALL, 0)
        sizer2.Add((-1,-1), 1, wx.EXPAND|wx.ALL, 0)
        sizer2.Add(staticText2_4, 0, wx.RIGHT, 20)
        sizer2.Add(staticText2_5, 0, wx.RIGHT, 10)
        sizer3 = wx.BoxSizer(wx.HORIZONTAL)
        sizer3.Add(staticText3, 0, wx.ALL, 0)
        sizer3.Add((-1,-1), 1, wx.EXPAND|wx.ALL, 0)
        sizer3.Add(checkBox3, 0, wx.RIGHT, 10)
        dlgSizer = wx.BoxSizer(wx.VERTICAL)
        dlgSizer.Add((-1,5), 0, wx.EXPAND|wx.ALL, 0)
        dlgSizer.Add(sizer01, 0, wx.EXPAND|wx.ALL, 5)
        dlgSizer.Add(wx.StaticLine(dlg, style=wx.HORIZONTAL), 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)
        #~ dlgSizer.Add(staticText2, 0, wx.EXPAND|wx.TOP|wx.LEFT, 5)
        dlgSizer.Add(sizer2, 0, wx.EXPAND|wx.TOP|wx.LEFT, 5)
        dlgSizer.Add(textCtrl2, 1, wx.EXPAND|wx.ALL, 5)
        #~ dlgSizer.Add(staticText3, 0, wx.TOP|wx.LEFT, 5)
        dlgSizer.Add(sizer3, 0, wx.EXPAND|wx.TOP|wx.LEFT, 5)
        dlgSizer.Add(textCtrl3, 0, wx.EXPAND|wx.ALL, 5)
        dlgSizer.Add(btns, 0, wx.EXPAND|wx.ALL, 5)
        dlg.SetSizer(dlgSizer)
        if not resetargsbutton:
            staticText2_5.Hide()
        def SetAutopreset(on=True):
            if on:
                checkBox3.SetValue(True)
                textCtrl3.SetEditable(False)
                colour = self.GetBackgroundColour()
                textCtrl3.SetBackgroundColour(colour)
            else:
                checkBox3.SetValue(False)
                textCtrl3.SetEditable(True)
                textCtrl3.SetBackgroundColour(wx.WHITE)
        dlg.SetAutopreset = SetAutopreset
        dlg.Fit()
        dlgSizer.Layout()
        # Bind variables
        dlg.nameBox = textCtrl0
        dlg.typeBox = choiceBox1
        dlg.argsBox = textCtrl2
        dlg.presetBox = textCtrl3
        dlg.autopresetCheckbox = checkBox3
        dlg.cancelButton = cancel
        dlg.defaultArgs = ''
        dlg.defaultName = ''
        dlg.enteredName = ''
        self.FilterInfoDialog = dlg

    def CheckAllFunctions(self, check=True):
        listbox = self.notebook.GetCurrentPage().listbox
        for i in xrange(listbox.GetCount()):
            listbox.Check(i, check)

    def _x_ClearLongNames(self):
        listbox = self.notebook.GetCurrentPage().listbox
        for i in xrange(listbox.GetCount()):
            if listbox.GetString(i).count('_') > 0:
                listbox.Check(i, False)

    def SelectInstalledFilters(self):
        listbox = self.notebook.GetCurrentPage().listbox
        for i in xrange(listbox.GetCount()):
            boolCheck = (listbox.GetString(i).split()[0].lower() in self.installedFilternames)
            listbox.Check(i, boolCheck)
            
    def ImportFromFiles(self):
        filenames, filterInfo, unrecognized = [], [], []
        title = _('Open Customization files, Avisynth scripts or Avsp options files')
        recentdir = os.path.join(self.GetParent().options['avisynthdir'], 'plugins')
        filefilter = _('All supported|*.txt;*.avsi;*.avs;*.dat|Customization file (*.txt)|*.txt|AviSynth script (*.avs, *.avsi)|*.avs;*.avsi|AvsP data (*.dat)|*.dat|All files (*.*)|*.*')
        dlg = wx.FileDialog(self, title, recentdir, '', filefilter, 
                            wx.OPEN|wx.MULTIPLE|wx.FILE_MUST_EXIST)
        ID = dlg.ShowModal()
        if ID == wx.ID_OK:
            filenames = dlg.GetPaths()            
        dlg.Destroy()
        if not filenames:
            return
            
        for filename in filenames:
            ext = os.path.splitext(filename)[1]
            try:
                if ext in ['.avs', '.avsi']:
                    info = self.ParseAvisynthScript(filename)
                elif ext == '.txt':
                    info = self.ParseCustomizations(filename)
                elif ext == '.dat':
                    f = open(filename, 'rb')
                    data = cPickle.load(f)
                    f.close()
                    info = []
                    for filtername, filterargs, ftype in data['filteroverrides'].values():
                        info.append((filename, filtername, filterargs, ftype))
                else:
                    info = None
            except:
                info = None
            if not info:
                unrecognized.append(filename)
            else:
                filterInfo += info
        if filterInfo and not self.checkBox.IsChecked():
            self.SelectImportFilters(filterInfo)
        for filename, filtername, filterargs, ftype in filterInfo:
            self.EditFunctionInfo(filtername, filterargs, ftype)
        if unrecognized:
            wx.MessageBox('\n'.join(unrecognized), _('Unrecognized files'))
    
    def SelectImportFilters(self, filterInfo):
        choices = []
        filterInfo.sort()
        for filename, filtername, filterargs, ftype in filterInfo:
            choices.append(os.path.basename(filename) + ' -> ' + filtername)
        dlg = wx.Dialog(self, wx.ID_ANY, _('Select import functions'), style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        listbox = wx.CheckListBox(dlg, wx.ID_ANY, choices=choices)
        for i in range(len(choices)):
            filename, filtername = choices[i].lower().split(' -> ')
            if filtername in self.overrideDict:
                listbox.SetItemForegroundColour(i, wx.RED)
            elif filename.find(filtername) != -1:
                listbox.Check(i)    
        idAll = wx.NewId()
        idNone = wx.NewId()
        idFileAll = wx.NewId()
        idFileNone = wx.NewId()
        def OnContextMenuItem(event):
            id = event.GetId()
            value = True if id in [idAll, idFileAll] else False
            if id in [idAll, idNone]:
                for i in range(len(choices)):
                    listbox.Check(i, value)
            else:
                pos = listbox.GetSelection()
                if pos != wx.NOT_FOUND:
                    filename = filterInfo[pos][0]
                    for i in range(len(choices)):
                        if filename == filterInfo[i][0]:
                            listbox.Check(i, value)
        def OnContextMenu(event):
            listbox.Bind(wx.EVT_MENU, OnContextMenuItem, id=idAll)
            listbox.Bind(wx.EVT_MENU, OnContextMenuItem, id=idNone)
            listbox.Bind(wx.EVT_MENU, OnContextMenuItem, id=idFileAll)
            listbox.Bind(wx.EVT_MENU, OnContextMenuItem, id=idFileNone)
            menu = wx.Menu()
            menu.Append(idAll, _('select all'))
            menu.Append(idNone, _('select none'))
            menu.Append(idFileAll, _('select all (file only)'))
            menu.Append(idFileNone, _('select none (file only)'))
            listbox.PopupMenu(menu)
            menu.Destroy()
        listbox.Bind(wx.EVT_CONTEXT_MENU, OnContextMenu)
        message = wx.StaticText(dlg, wx.ID_ANY, _('Red - a customized function already exists.'))
        okay  = wx.Button(dlg, wx.ID_OK, _('OK'))
        cancel = wx.Button(dlg, wx.ID_CANCEL, _('Cancel'))
        btns = wx.StdDialogButtonSizer()
        btns.AddButton(okay)
        btns.AddButton(cancel)
        btns.Realize()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(listbox, 1, wx.EXPAND|wx.ALL,5)        
        sizer.Add(message, 0, wx.LEFT, 5)
        sizer.Add(btns, 0, wx.EXPAND|wx.ALL,5)
        dlg.SetSizerAndFit(sizer)
        ID = dlg.ShowModal()
        for i in range(len(choices)-1, -1, -1):
            if ID != wx.ID_OK or not listbox.IsChecked(i):
                del filterInfo[i]
        dlg.Destroy()
        
    def ParseAvisynthScript(self, filename):
        pattern = r'function\s+(\w+)\s*\((.*?)\)\s*\{(.+?)\}'
        default = r'default\s*\(\s*%s\s*,\s*(.+?)\s*\)'
        filterInfo, text = [], []
        f = open(filename)
        for line in f:
            line = line.strip()
            line = line.strip('\\')
            if not line.startswith('#'):
                text.append(line)
        f.close()
        text = ' '.join(text)
        matches = re.findall(pattern, text, re.I|re.S)
        for filtername, args, body in matches:
            text = ['(\n']
            varnameDict = {}
            if args.strip():
                for arg in args.split(','):
                    arg = arg.split()
                    if len(arg) == 2:
                        vartype, varname = arg
                    elif len(arg) == 1:
                        sep = arg[0].find('"') 
                        vartype = arg[0][:sep]
                        varname = arg[0][sep:]
                    else:
                        return None
                    text.append(vartype)
                    if varname[0] == '"':
                        text += [' ', varname]
                        varname = varname[1:-1]
                        pat = default % varname
                        ret = re.search(pat, body, re.I|re.S)
                        if ret:
                            value = ret.group(1)
                            if vartype not in ['int', 'float'] or value.isdigit():
                                text += ['=', value]
                                varnameDict[varname] = value
                            else:
                                for name in varnameDict:
                                    value = value.replace(name, varnameDict[name])
                                try:
                                    value = str(eval(value))
                                    text += ['=', value]
                                    varnameDict[varname] = value
                                except:
                                    print _('Error'), 'ParseAvisynthScript() try eval(%s)' % value                                  
                    text.append(',\n')
            if text[-1] == ',\n':
                text[-1] = '\n'
            text.append(')')
            filterargs = ''.join(text)
            filterInfo.append((filename, filtername, filterargs, 3))
        return filterInfo
        
    def ParseCustomizations(self, filename):
        f = open(filename)
        text = '\n'.join([line.strip() for line in f.readlines()])
        f.close()
        filterInfo = []
        for section in text.split('\n['):
            title, data = section.split(']\n',1)
            title = title.strip('[]').lower()
            if title == 'clipproperties':
                for item in data.split('\n'):
                    if not item.strip():
                        continue
                    splitstring = item.split('(', 1)
                    if len(splitstring) == 2:
                        filtername = splitstring[0].strip()
                        filterargs = '('+splitstring[1].strip(' ')
                    else:
                        filtername = item
                        filterargs = ''
                    filterInfo.append((filename, filtername, filterargs, 1))
            elif title == 'scriptfunctions':
                for item in data.split('\n'):
                    splitstring = item.split('(', 1)
                    if len(splitstring) == 2:
                        filtername = splitstring[0].strip()
                        filterargs = '('+splitstring[1].strip(' ')
                        filterInfo.append((filename, filtername, filterargs, 4))
            elif title == 'corefilters':
                for s in data.split('\n\n'):
                    splitstring = s.split('(', 1)
                    if len(splitstring) == 2:
                        filtername = splitstring[0].strip()
                        filterargs = '('+splitstring[1].strip(' ')
                        filterInfo.append((filename, filtername, filterargs, 0))
            elif title == 'plugins':
                for s in data.split('\n\n'):
                    splitstring = s.split('(', 1)
                    if len(splitstring) == 2:
                        filtername = splitstring[0].strip()
                        filterargs = '('+splitstring[1].strip(' ')
                        filterInfo.append((filename, filtername, filterargs, 2))
            elif title == 'userfunctions':
                for s in data.split('\n\n'):
                    splitstring = s.split('(', 1)
                    if len(splitstring) == 2:
                        filtername = splitstring[0].strip()
                        filterargs = '('+splitstring[1].strip(' ')
                        filterInfo.append((filename, filtername, filterargs, 3))
        return filterInfo
                
    def ExportCustomizations(self):
        if len(self.overrideDict) == 0:
            wx.MessageBox(_('No customizations to export!'), _('Error'), style=wx.OK|wx.ICON_ERROR)
            return
        title = _('Save filter customizations')
        recentdir = self.GetParent().programdir
        filefilter = _('Customization file (*.txt)|*.txt|All files (*.*)|*.*')
        dlg = wx.FileDialog(self, title, recentdir, '', filefilter, wx.SAVE|wx.OVERWRITE_PROMPT)
        ID = dlg.ShowModal()
        if ID == wx.ID_OK:
            filename = dlg.GetPath()
            self.ExportFilterData(self.overrideDict, filename)
        dlg.Destroy()

    def ClearCustomizations(self):
        dlg = wx.MessageDialog(self, _('This will delete all filter customizations. Continue?'), _('Warning'), wx.YES_NO)
        ID = dlg.ShowModal()
        if ID == wx.ID_YES:
            #~ for lowername, (name, args, ftype) in self.overrideDict.items():
                #~ originalName = self.filterDict.get(lowername, [name])[0]
                #~ newName = originalName+' '
                #~ adjustedName = name+' '
                #~ if lowername in self.overrideDict:
                    #~ adjustedName += '*'
                #~ if lowername in self.presetDict:
                    #~ adjustedName += '~'
                    #~ newName += '~'
                #~ if newName != adjustedName:
                    #~ for index in xrange(self.notebook.GetPageCount()):
                        #~ panel = self.notebook.GetPage(index)
                        #~ if panel.functiontype == ftype:
                            #~ listbox = panel.listbox
                            #~ foundindex = listbox.FindString(adjustedName)
                            #~ if foundindex != wx.NOT_FOUND:
                                #~ listbox.SetString(foundindex, newName)
                            #~ break
            self.overrideDict = {}
            self.RefreshListNames()
        dlg.Destroy()

    def ClearPresets(self):
        dlg = wx.MessageDialog(self, _('This will delete all manually defined presets. Continue?'), _('Warning'), wx.YES_NO)
        ID = dlg.ShowModal()
        if ID == wx.ID_YES:
            #~ for lowername in self.presetDict.keys():
                #~ value = self.overrideDict.get(lowername)
                #~ if value is None:
                    #~ value = self.filterDict[lowername]
                #~ name, args, ftype = value
                #~ newName = name+' '
                #~ adjustedName = name+' '
                #~ if lowername in self.overrideDict:
                    #~ adjustedName += '*'
                    #~ newName += '*'
                #~ if lowername in self.presetDict:
                    #~ adjustedName += '~'
                #~ if newName != adjustedName:
                    #~ for index in xrange(self.notebook.GetPageCount()):
                        #~ panel = self.notebook.GetPage(index)
                        #~ if panel.functiontype == ftype:
                            #~ listbox = panel.listbox
                            #~ foundindex = listbox.FindString(adjustedName)
                            #~ if foundindex != wx.NOT_FOUND:
                                #~ listbox.SetString(foundindex, newName)
                            #~ break
            self.presetDict = {}
            self.RefreshListNames()
        dlg.Destroy()
        
    def RefreshListNames(self):
        for index in xrange(self.notebook.GetPageCount()):
            panel = self.notebook.GetPage(index)
            listbox = panel.listbox
            deleteIndices = []
            for i in xrange(listbox.GetCount()):
                name = listbox.GetString(i).split()[0]
                lowername = name.lower()
                extra = ' '
                if lowername in self.overrideDict:
                    extra += '*'
                elif lowername not in self.filterDict:
                    deleteIndices.append(i)
                    continue
                if lowername in self.presetDict:
                    extra += '~'
                newname = name+extra
                if listbox.GetString(i) != newname:
                    listbox.SetString(i, newname)
            deleteIndices.reverse()
            for i in deleteIndices:
                listbox.Delete(i)

    def AddNewFunction(self, name='', ftype=3, arg=None):
        dlg = self.FilterInfoDialog
        if ftype == -1:
            index = self.notebook.GetSelection()
            if index != wx.NOT_FOUND:
                ftype = self.notebook.GetPage(index).functiontype
            else:
                ftype = 3
        else:
            for index in xrange(self.notebook.GetPageCount()):
                panel = self.notebook.GetPage(index)
                if panel.functiontype == ftype:
                    self.notebook.SetSelection(index)
                    break
        #~ lowername = name.lower()
        #~ defaultValues = self.filterDict.get(lowername)
        #~ enteredValues = self.overrideDict.get(lowername, defaultValues)
        #~ if enteredValues is not None:
            #~ enteredName, enteredArgs, enteredType = enteredValues
            #~ defaultName, defaultArgs, defaultType = defaultValues
        #~ else:
            #~ enteredName, enteredArgs, enteredType = ('', '', 3)
            #~ defaultName, defaultArgs, defaultType = (None, None, None)
        #~ enteredPreset = self.presetDict.get(lowername)#, defaultPreset)
        #~ if enteredPreset is not None:
            #~ dlg.SetAutopreset(False)
        #~ else:
            #~ dlg.SetAutopreset(True)
            #~ enteredPreset = self.CreateDefaultPreset(name, enteredArgs)
        defaultName = name
        defaultArgs = '()' if not arg else arg
        dlg.nameBox.SetValue(defaultName)
        dlg.typeBox.SetSelection(ftype)
        dlg.typeBox.Enable()
        dlg.argsBox.SetValue(defaultArgs)
        dlg.presetBox.SetValue('')
        dlg.SetAutopreset(True)
        dlg.cancelButton.SetFocus()
        dlg.defaultArgs = defaultArgs
        dlg.defaultName = defaultName
        dlg.enteredName = None
        if arg: ID = wx.ID_OK
        else: ID = dlg.ShowModal()
        if ID == wx.ID_OK:
            newName = dlg.nameBox.GetValue()
            newType = dlg.typeBox.GetSelection()
            newArgs = dlg.argsBox.GetValue()
            newPreset = dlg.presetBox.GetValue()
            boolAutoPreset = dlg.autopresetCheckbox.GetValue()
            for index in xrange(self.notebook.GetPageCount()):
                panel = self.notebook.GetPage(index)
                if panel.functiontype == newType:
                    self.notebook.SetSelection(index)
                    listbox = panel.listbox
                    break
            #else:
                #return
            extra = ' '
            # Update the override dict
            #~ if (newName != defaultName) or (newArgs != defaultArgs):
                #~ self.overrideDict[lowername] = (newName, newArgs, newType)
                #~ extra += '*'
            #~ else:
                #~ if lowername in self.overrideDict:
                    #~ del self.overrideDict[lowername]
            lowername = newName.lower()
            self.overrideDict[lowername] = (newName, newArgs, newType)
            extra += '*'
            # Update the preset dict
            if boolAutoPreset:
                if lowername in self.presetDict:
                    del self.presetDict[lowername]
            else:
                self.presetDict[lowername] = newPreset
                extra += '~'
            #~ listbox.SetString(listbox.GetSelection(), newName+extra)
            index = listbox.Append(newName+extra)
            listbox.Check(index)
            listbox.SetSelection(index)
            listbox.SetFirstItem(index)

    def EditFunctionInfo(self, name=None, arg=None, ftype=None):
        dlg = self.FilterInfoDialog
        if arg:
            arg = arg.strip()
            name = unicode(name)
            for index in xrange(self.notebook.GetPageCount()):
                panel = self.notebook.GetPage(index)
                if panel.functiontype == ftype:
                    break
        else:
            panel = self.notebook.GetCurrentPage()
        listbox = panel.listbox
        functiontype = panel.functiontype
        if name is None:
            name = listbox.GetStringSelection().split()[0]
        if not name:
            return
        lowername = name.lower()
        if lowername not in self.filterDict and lowername not in self.overrideDict:
            if not ftype:
                self.AddNewFunction(name)
            else:
                self.AddNewFunction(name, ftype, arg)
            return
        # Fill out default values
        #~ defaultName = self.filterDict[lowername][0]
        #~ defaultArgs = self.filterDict[lowername][1]
        defaultName, defaultArgs, defaultType = self.filterDict.get(lowername, ('', '', None))
        #~ defaultPreset = self.CreateDefaultPreset(name, defaultArgs)
        enteredName = name
        enteredType = functiontype
        enteredArgs = self.overrideDict.get(lowername, (None, defaultArgs, None))[1] if not arg else arg
        #~ defaultPreset = self.CreateDefaultPreset(name, enteredArgs)
        enteredPreset = self.presetDict.get(lowername)#, defaultPreset)
        if enteredPreset is not None:
            dlg.SetAutopreset(False)
        else:
            dlg.SetAutopreset(True)
            enteredPreset = self.CreateDefaultPreset(name, enteredArgs)
        dlg.nameBox.SetValue(enteredName)
        dlg.typeBox.SetSelection(enteredType)
        dlg.argsBox.SetValue(enteredArgs)
        dlg.presetBox.SetValue(enteredPreset)
        if lowername in self.filterDict:
            dlg.typeBox.Disable()
        else:
            dlg.typeBox.Enable()
        dlg.cancelButton.SetFocus()
        dlg.defaultArgs = defaultArgs
        #~ self.defaultPreset = defaultPreset
        dlg.defaultName = defaultName
        dlg.enteredName = enteredName
        if arg: ID = wx.ID_OK
        else: ID = dlg.ShowModal()
        if ID == wx.ID_OK:
            newName = dlg.nameBox.GetValue()
            newType = dlg.typeBox.GetSelection()
            newArgs = dlg.argsBox.GetValue()
            newPreset = dlg.presetBox.GetValue()
            boolAutoPreset = dlg.autopresetCheckbox.GetValue()
            extra = ' '
            # Update the override dict
            if (newName != defaultName) or (newArgs != defaultArgs):
                self.overrideDict[lowername] = (newName, newArgs, newType)
                extra += '*'
            else:
                if lowername in self.overrideDict:
                    del self.overrideDict[lowername]
            # Update the preset dict
            if boolAutoPreset:
                if lowername in self.presetDict:
                    del self.presetDict[lowername]
            else:
                self.presetDict[lowername] = newPreset
                extra += '~'
            if newType == enteredType:
                if arg:
                    for i in xrange(listbox.GetCount()):
                        if newName == listbox.GetString(i).split()[0]:
                            listbox.SetSelection(i)
                            break
                listbox.SetString(listbox.GetSelection(), newName+extra)
            else:
                for index in xrange(self.notebook.GetPageCount()):
                    panel = self.notebook.GetPage(index)
                    if panel.functiontype == newType:
                        listindex = listbox.GetSelection()
                        ischecked = listbox.IsChecked(listindex)
                        listbox.Delete(listindex)
                        listindex = panel.listbox.Append(newName+extra)
                        panel.listbox.SetSelection(listindex)
                        panel.listbox.SetFirstItem(listindex)
                        panel.listbox.Check(listindex, ischecked)
                        self.notebook.SetSelection(index)
                        break
                else:
                    return

    def DeleteFunction(self):
        listbox = self.notebook.GetCurrentPage().listbox
        index = listbox.GetSelection()
        if index == wx.NOT_FOUND:
            return
        name = listbox.GetString(index).split()[0]
        lowername = name.lower()
        listbox.Check(index, False)
        if lowername not in self.filterDict:
            dlg = wx.MessageDialog(self, _('Do you want to delete this custom filter entirely?'), _('Warning'), wx.YES_NO)
            ID = dlg.ShowModal()
            if ID == wx.ID_YES:
                if lowername in self.overrideDict:
                    del self.overrideDict[lowername]
                    if lowername in self.presetDict:
                        del self.presetDict[lowername]
                listbox.Delete(index)
            dlg.Destroy()

    def GetOverrideDict(self):
        return self.overrideDict

    def GetPresetDict(self):
        return self.presetDict

    def GetRemovedSet(self):
        removedList = []
        for index in xrange(self.notebook.GetPageCount()):
            listbox = self.notebook.GetPage(index).listbox
            for i in xrange(listbox.GetCount()):
                if not listbox.IsChecked(i):
                    removedList.append(listbox.GetString(i).split()[0].lower())
        return set(removedList)

    def GetAutcompletetypeFlags(self):
        flags = [True,True,True,True,True]
        for i in xrange(self.notebook.GetPageCount()):
            panel = self.notebook.GetPage(i)
            index = panel.functiontype
            checkbox = panel.autocompletecheckbox
            flags[index] = checkbox.GetValue()
        return flags
        
# Dialog specifically for AviSynth filter auto-slider information
class AvsFilterAutoSliderInfo(wx.Dialog):
    def __init__(self, parent, mainFrame, filterName, filterInfo, title=_('Edit filter database')):
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.mainFrame = mainFrame
        self.newFilterInfo = None
        # Filter name label
        filterLabel = wx.StaticText(self, wx.ID_ANY, filterName)
        font = filterLabel.GetFont()
        font.SetPointSize(10)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        filterLabel.SetFont(font)
        # Arguments
        argWindow = wx.ScrolledWindow(self, wx.ID_ANY, style=wx.TAB_TRAVERSAL)
        argWindow.SetScrollRate(10, 10)
        argSizer = wx.GridBagSizer(hgap=0, vgap=10)
        row = 0
        self.argctrls = []
        for argInfo in self.mainFrame.currentScript.GetFilterCalltipArgInfo(calltip=filterInfo):
            totalInfo, cArgType, cArgName, boolRepeatArg, cArgInfo = argInfo
            argtype, argname, guitype, defaultValue, other = self.mainFrame.ParseCalltipArgInfo(totalInfo)
            #~ if guitype is None or argname is None or argtype not in ('int', 'float', 'bool', 'string'):
            if argname is None or argtype not in ('int', 'float', 'bool', 'string'):
                self.argctrls.append((argtype, argname, None, boolRepeatArg))
            else:
                argLabel = wx.StaticText(argWindow, wx.ID_ANY, '%(argtype)s %(argname)s' % locals())
                argLabel.controls = []
                argSizer.Add(argLabel, (row,0), wx.DefaultSpan, wx.ALIGN_RIGHT|wx.ALIGN_BOTTOM|wx.BOTTOM|wx.RIGHT, 5)
                if argtype in ('int', 'float'):
                    strDefaultValue = strMinValue = strMaxValue = strMod = ''
                    if other is not None:
                        minValue, maxValue, nDecimal, mod = other
                        if nDecimal is None:
                            nDecimal = 0
                        strTemplate = '%.'+str(nDecimal)+'f'
                        if defaultValue is not None:
                            try:
                                strDefaultValue = strTemplate % defaultValue
                            except TypeError:
                                strDefaultValue = defaultValue
                        if minValue is not None:
                            try:
                                strMinValue = strTemplate % minValue
                            except TypeError:
                                strMinValue = minValue
                        if maxValue is not None:
                            try:
                                strMaxValue = strTemplate % maxValue
                            except TypeError:
                                strMaxValue = maxValue
                        if mod is not None:
                            try:
                                strMod = '%i' % mod
                            except TypeError:
                                strMod = mod
                    elif guitype == 'color':
                        strDefaultValue = '$%s' % defaultValue
                    itemData = (
                        (strDefaultValue, _('Default')),
                        (strMinValue, _('Min value')),
                        (strMaxValue, _('Max value')),
                        (strMod, _('Step size')),
                    )
                    hsizer = wx.BoxSizer(wx.HORIZONTAL)
                    for itemValue, itemName in itemData:
                        itemLabel = wx.StaticText(argWindow, wx.ID_ANY, itemName)
                        itemTextCtrl = wx.TextCtrl(argWindow, wx.ID_ANY, itemValue,size=(75,-1))
                        vsizer = wx.BoxSizer(wx.VERTICAL)
                        vsizer.Add(itemLabel, 0, wx.LEFT, 2)
                        vsizer.Add(itemTextCtrl, 0, wx.ALL, 0)
                        hsizer.Add(vsizer, 0, wx.EXPAND|wx.RIGHT,5)
                        argLabel.controls.append(itemTextCtrl)
                    argSizer.Add(hsizer, (row,1), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 0)
                elif argtype == 'bool':
                    strDefaultValue = ''
                    if defaultValue is not None:
                        if defaultValue.lower() == 'true':
                            strDefaultValue = 'True'
                        if defaultValue.lower() == 'false':
                            strDefaultValue = 'False'
                    itemLabel = wx.StaticText(argWindow, wx.ID_ANY, _('Default'))
                    itemTextCtrl = wx.ComboBox(argWindow, wx.ID_ANY, strDefaultValue, choices=['True', 'False'], style=wx.CB_DROPDOWN, size=(75,-1))
                    vsizer = wx.BoxSizer(wx.VERTICAL)
                    vsizer.Add(itemLabel, 0, wx.LEFT, 2)
                    vsizer.Add(itemTextCtrl, 0, wx.ALL, 0)
                    argLabel.controls.append(itemTextCtrl)
                    argSizer.Add(vsizer, (row,1), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 0)
                elif argtype == 'string':
                    strDefaultValue = strValuesList = ''
                    if defaultValue is not None:
                        if defaultValue:
                            strDefaultValue = '"%s"' % defaultValue.strip('"')
                    if other is not None:
                        strValuesList = ', '.join(other)
                    hsizer = wx.BoxSizer(wx.HORIZONTAL)
                    # Default control
                    itemLabel = wx.StaticText(argWindow, wx.ID_ANY, _('Default'))
                    itemTextCtrl = wx.TextCtrl(argWindow, wx.ID_ANY, strDefaultValue, size=(75,-1))
                    vsizer = wx.BoxSizer(wx.VERTICAL)
                    vsizer.Add(itemLabel, 0, wx.LEFT, 2)
                    vsizer.Add(itemTextCtrl, 0, wx.ALL, 0)
                    argLabel.controls.append(itemTextCtrl)
                    hsizer.Add(vsizer, 0, wx.EXPAND|wx.RIGHT,5)
                    # Values control
                    itemLabel = wx.StaticText(argWindow, wx.ID_ANY, _('Value list (comma separated)'))
                    itemTextCtrl = wx.TextCtrl(argWindow, wx.ID_ANY, strValuesList, size=(200,-1))
                    vsizer = wx.BoxSizer(wx.VERTICAL)
                    vsizer.Add(itemLabel, 0, wx.LEFT, 2)
                    vsizer.Add(itemTextCtrl, 1, wx.EXPAND|wx.ALL, 0)
                    argLabel.controls.append(itemTextCtrl)
                    hsizer.Add(vsizer, 1, wx.EXPAND|wx.RIGHT,5)

                    argSizer.Add(hsizer, (row,1), wx.DefaultSpan, wx.EXPAND|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 0)

                row += 1
                self.argctrls.append((argtype, argname, argLabel, boolRepeatArg))
        argWindow.SetSizer(argSizer)
        # Standard buttons
        okay  = wx.Button(self, wx.ID_OK, _('OK'))
        self.Bind(wx.EVT_BUTTON, self.OnButtonOK, okay)
        okay.SetDefault()
        cancel = wx.Button(self, wx.ID_CANCEL, _('Cancel'))
        btns = wx.StdDialogButtonSizer()
        btns.AddButton(okay)
        btns.AddButton(cancel)
        btns.Realize()
        # Set the sizer
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add((-1,-1), 0, wx.TOP, 10)
        sizer.Add(filterLabel, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(wx.StaticLine(self, wx.ID_ANY), 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 5)
        sizer.Add(argWindow, 1, wx.EXPAND|wx.ALL, 5)
        sizer.Add(wx.StaticLine(self, wx.ID_ANY), 0, wx.EXPAND|wx.LEFT|wx.RIGHT, 5)
        #~ sizer.Add(wx.StaticText(self,wx.ID_ANY, _('* optional value')), 0, wx.EXPAND|wx.ALL, 10)
        sizer.Add(btns, 0, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(sizer)
        sizer.Layout()
        argWindow.FitInside()
        w = max(argSizer.GetMinSize()[0]+50, 300)
        h = 500
        self.SetSize((w,h))

    def OnButtonOK(self, event):
        strList = []
        for argtype, argname, argLabel, boolRepeatArg in self.argctrls:
            if argtype is None and argname is None:
                continue
            strBase = '%(argtype)s %(argname)s' % locals()
            if argLabel is None:
                if argname is None:
                    strList.append(argtype)
                else:
                    strList.append(strBase)
            else:
                strInfoNew = strBase
                strDef = argLabel.controls[0].GetValue().strip()
                #~ strList.append('%(strBase)s=%(strDefaultValue)s' % locals())
                if argtype in ('int', 'float'):
                    strMin = argLabel.controls[1].GetValue().strip()
                    strMax = argLabel.controls[2].GetValue().strip()
                    strMod = argLabel.controls[3].GetValue().strip()
                    # Validate if any field has input
                    sliderValues = None
                    if strDef or strMin or strMax or strMod:
                        errorType, errorMessage, sliderValues = self.mainFrame.ValidateAvsSliderInputs(strDef, strMin, strMax, strMod)
                        if errorType is not None and errorType != -1:
                            self.ShowWarning(argLabel.controls[errorType], '%(argtype)s %(argname)s: %(errorMessage)s' % locals())
                            return
                    # Create the new string info
                    #~ if sliderValues is not None and len(sliderValues) == 1:
                    if strDef and not strMin and not strMax:
                        strInfoNew = '%(strBase)s=%(strDef)s' % locals()
                    elif not strMin and not strMax:
                        strInfoNew = strBase
                    elif strMod:
                        strInfoNew = '%(strBase)s=%(strDef)s (%(strMin)s to %(strMax)s by %(strMod)s)' % locals()
                    else:
                        strInfoNew = '%(strBase)s=%(strDef)s (%(strMin)s to %(strMax)s)' % locals()
                elif argtype == 'bool':
                    if strDef:
                        if strDef.lower() not in ('true', 'false'):
                            self.ShowWarning(argLabel.controls[0], '%s %s: %s' % (argtype, argname, _('Value must be True or False!')), comboBox=True)
                            return
                        strInfoNew = '%(strBase)s=%(strDef)s' % locals()
                elif argtype == 'string':
                    strValues = argLabel.controls[1].GetValue().strip()
                    if strDef or strValues:
                        if not strValues:
                            msg =  _('Must enter a value list!')
                            #~ self.ShowWarning(argLabel.controls[1], '%s %s: %s' % (argtype, argname,msg))
                            #~ return
                            pass
                        strValuesNew = '/ '.join(['"%s"' % s.strip(' "') for s in strValues.split(',')])
                        if strDef:
                            strDef = '"%s"' % strDef.strip('"')
                        strInfoNew = '%(strBase)s=%(strDef)s (%(strValuesNew)s)' % locals()
                strRepeatArg = ''
                if boolRepeatArg:
                    strRepeatArg = ' [, ...]'
                strList.append(strInfoNew+strRepeatArg)
        self.newFilterInfo = '(\n%s\n)' % ',\n'.join(strList)
        event.Skip()

    def GetNewFilterInfo(self):
        return self.newFilterInfo

    def ShowWarning(self, textCtrl, message, comboBox=False):
        color = textCtrl.GetBackgroundColour()
        textCtrl.SetBackgroundColour('pink')
        textCtrl.Refresh()
        wx.MessageBox(message, _('Error'), style=wx.OK|wx.ICON_ERROR)
        textCtrl.SetBackgroundColour(color)
        textCtrl.Refresh()
        textCtrl.GetParent().Refresh()
        if comboBox:
            textCtrl.SetMark(-1,-1)
        else:
            textCtrl.SetSelection(-1,-1)
        textCtrl.SetFocus()
        textCtrl.Refresh()

# Dialog for filter customization exporting/importing
class AvsFunctionExportImportDialog(wx.Dialog):
    def __init__(self, parent, infoDict, export=True):
        self.export = export
        if export:
            title = _('Export filter customizations')
        else:
            title = _('Import filter customizations')
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title, size=(500, 300), style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        self.calltipDict = infoDict[0]
        self.presetDict = infoDict[1]
        self.docpathDict = infoDict[2]
        self.functiontypeDict = infoDict[3]

        # Create the list control using the dictionary
        decList = [(s.lower(), s) for s in self.calltipDict.keys()]
        decList.sort()
        self.names = [s[1] for s in decList]
        self.checkListBox = wx.CheckListBox(self, wx.ID_ANY, choices=self.names)

        # Create extra control buttons
        def OnButtonSelectAll(event):
            for index in xrange(len(self.names)):
                self.checkListBox.Check(index, True)
        def OnButtonClearAll(event):
            for index in xrange(len(self.names)):
                self.checkListBox.Check(index, False)
        buttonSelectAll = wx.Button(self, wx.ID_ANY, _('Select all'))
        self.Bind(wx.EVT_BUTTON, OnButtonSelectAll, buttonSelectAll)
        buttonClearAll = wx.Button(self, wx.ID_ANY, _('Clear all'))
        self.Bind(wx.EVT_BUTTON, OnButtonClearAll, buttonClearAll)

        if export:
            staticText = wx.StaticText(self, wx.ID_ANY, _('Select filters to export:'))
            extraItem = (-1, 20)
        else:
            staticText = wx.StaticText(self, wx.ID_ANY, _('Select filters to import from the file:'))
            # Import dialog, check all names by default
            for index in xrange(len(self.names)):
                self.checkListBox.Check(index)
            # Extra controls to provide options for import information
            #~ self.checkBoxCalltip = wx.CheckBox(self, wx.ID_ANY, _('Calltips'))
            #~ self.checkBoxPreset = wx.CheckBox(self, wx.ID_ANY, _('Presets'))
            #~ self.checkBoxDocpath = wx.CheckBox(self, wx.ID_ANY, _('Docpaths'))
            #~ self.checkBoxType = wx.CheckBox(self, wx.ID_ANY, _('Filter types'))
            #~ staticBox = wx.StaticBox(self, wx.ID_ANY, _('Import from filters:'))
            #~ staticBoxSizer = wx.StaticBoxSizer(staticBox, wx.HORIZONTAL)
            #~ for item in (self.checkBoxCalltip, self.checkBoxPreset, self.checkBoxDocpath, self.checkBoxType):
                #~ item.SetValue(True)
                #~ staticBoxSizer.Add(item, 0, wx.ALL, 5)
            self.checkBoxOverwriteAll = wx.CheckBox(self, wx.ID_ANY, _('Overwrite all data'))
            self.checkBoxOverwriteAll.SetValue(True)
            extraItem = wx.BoxSizer(wx.VERTICAL)
            #~ extraItem.Add(staticBoxSizer, 0, wx.BOTTOM, 10)
            extraItem.Add(self.checkBoxOverwriteAll, 0, wx.LEFT|wx.BOTTOM, 5)

        # Standard buttons
        okay  = wx.Button(self, wx.ID_OK, _('OK'))
        self.Bind(wx.EVT_BUTTON, self.OnButtonOK, okay)
        cancel = wx.Button(self, wx.ID_CANCEL, _('Cancel'))
        btns = wx.StdDialogButtonSizer()
        btns.AddButton(okay)
        btns.AddButton(cancel)
        btns.Realize()

        # Size the elements
        buttonSizer = wx.BoxSizer(wx.VERTICAL)
        buttonSizer.Add(buttonSelectAll, 0, wx.ALL, 5)
        buttonSizer.Add(buttonClearAll, 0, wx.ALL, 5)
        listSizer = wx.BoxSizer(wx.HORIZONTAL)
        listSizer.Add(self.checkListBox, 1, wx.EXPAND|wx.ALL, 5)
        listSizer.Add(buttonSizer, 0, wx.ALL, 5)
        dlgSizer = wx.BoxSizer(wx.VERTICAL)
        dlgSizer.Add((-1,5))
        dlgSizer.Add(staticText, 0, wx.ALL, 5)
        dlgSizer.Add(listSizer, 1, wx.EXPAND|wx.LEFT|wx.RIGHT, 5)
        dlgSizer.Add(extraItem, 0, wx.ALL, 5)
        dlgSizer.Add(btns, 0, wx.EXPAND|wx.ALL, 5)
        self.SetSizer(dlgSizer)
        dlgSizer.SetSizeHints(self)
        # Misc
        okay.SetDefault()

    def OnButtonOK(self, event):
        self.dlgDataDict = {}
        # Build the dictionnary from the checked filters
        for i, name in enumerate(self.names):
            if self.checkListBox.IsChecked(i):
                calltip = self.calltipDict.get(name, '')
                preset = self.presetDict.get(name, '')
                docpath = self.docpathDict.get(name, '')
                ftype = self.functiontypeDict.get(name, '')
                self.dlgDataDict[name] = (calltip, preset, docpath, ftype)
        if not self.dlgDataDict:
            wx.MessageBox(_('You must select at least one filter!'), _('Warning'))
            return
        event.Skip()

    def GetData(self):
        return self.dlgDataDict

    def GetOverwriteAll(self):
        return self.checkBoxOverwriteAll.GetValue()

# Custom slider
class SliderPlus(wx.Panel):
    def __init__(self, parent, id, value=0, minValue=0, maxValue=100, size=(-1, 28), bookmarkDict={}):
        wx.Panel.__init__(self, parent, id, size=size, style=wx.WANTS_CHARS)
        self.bookmarkDict = bookmarkDict
        self.parent = parent
        self.minValue = minValue
        self.maxValue = maxValue
        self.value = max(min(value, self.maxValue), self.minValue)
        self.bookmarks = []
        # Internal display variables
        self.isclicked = False
        self.xdelta = None
        self.xo = 15
        self.yo = 5
        self.yo2 = 10
        self.wT = 22
        self.wH = 10
        self.selections = None
        self.selmode = 0
        self._DefineBrushes()
        # Event binding
        self.Bind(wx.EVT_PAINT, self._OnPaint)
        self.Bind(wx.EVT_SIZE, self._OnSize)
        self.Bind(wx.EVT_LEFT_DOWN, self._OnLeftDown)
        self.Bind(wx.EVT_MOTION, self._OnMouseMotion)
        self.Bind(wx.EVT_LEFT_UP, self._OnLeftUp)
        self.Bind(wx.EVT_MOUSEWHEEL, self._OnMouseWheel)
        self.Bind(wx.EVT_KEY_DOWN, self._OnKeyDown)
        def OnSetFocus(event):
            if not self.HasCapture():
                try:
                    event.GetWindow().SetFocus()
                except AttributeError:
                    event.Skip()
        self.Bind(wx.EVT_SET_FOCUS, OnSetFocus)

    def _DefineBrushes(self):
        #~ colorBackground = self.parent.GetBackgroundColour()
        colorBackground = self.GetBackgroundColour()
        colorHighlight = wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DLIGHT)
        colorHighlight2 = wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DHILIGHT)
        colorShadow = wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DSHADOW)
        colorDarkShadow = wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DDKSHADOW)
        colorWindow = colorHighlight2#wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
        #~ colorHandle = wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENU)
        colorHandle = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE)
        r,g,b = colorHandle.Red(), colorHandle.Green(), colorHandle.Blue()
        #~ colorHandle2 = wx.Colour(min(r+30, 255),min(g+30, 255),min(b+30, 255))#wx.SystemSettings.GetColour(wx.SYS_COLOUR_SCROLLBAR)
        colorHandle2 = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNHIGHLIGHT)
        colorGrayText = wx.SystemSettings.GetColour(wx.SYS_COLOUR_GRAYTEXT)
        self.penWindowBackground = wx.Pen(colorBackground)
        self.brushWindowBackground = wx.Brush(colorBackground)
        self.penBackground = wx.Pen(colorWindow)
        self.brushBackground = wx.Brush(colorWindow)
        self.penShadow = wx.Pen(colorShadow)
        self.penDarkShadow = wx.Pen(colorDarkShadow)
        self.penHighlight = wx.Pen(colorHighlight)
        self.penHighlight2 = wx.Pen(colorHighlight2)
        self.penHandle = wx.Pen(colorHandle)
        self.brushHandle = wx.Brush(colorHandle)
        self.penHandle2 = wx.Pen(colorHandle2)
        self.brushHandle2 = wx.Brush(colorHandle2)
        self.penGrayText = wx.Pen(colorGrayText)
        self.brushGrayText = wx.Brush(colorGrayText)

    def _OnLeftDown(self, event):
        mousepos = event.GetPosition()
        x, y, w, h = self.GetRect()
        #~ pixelpos = int(self.value * (w-2*self.xo) / float(self.maxValue - self.minValue))
        #~ rectHandle = wx.Rect(pixelpos-self.wH/2+self.xo, self.yo-3, self.wH, h-self.yo-self.yo2+6)
        rectHandle = self._getRectHandle()
        rectBox = wx.Rect(0, 0+self.yo, w, h-self.yo-self.yo2)
        if rectHandle.Inside(mousepos):
            self.isclicked = True
            self.xdelta = mousepos.x - rectHandle.x
            self.CaptureMouse()
            dc = wx.BufferedDC(wx.ClientDC(self))
            dc.Clear()
            self._PaintSlider(dc)
        elif self.selmode == 1 and self._HitTestHandleDeadZone(mousepos):
            pass
        elif rectBox.Inside(mousepos):
            self.isclicked = True
            self.CaptureMouse()
            oldvalue = self.value
            #~ self.SetValue(int(round((mousepos.x-self.xo+self.wH/2) * (self.maxValue - self.minValue) / float(w-2*self.xo))))
            self.SetValue(int(round((mousepos.x-self.xo) * (self.maxValue - self.minValue) / float(w-2*self.xo))))
            if self.value != oldvalue:
                self._SendScrollEvent()
            rectHandle = self._getRectHandle()
            self.xdelta = mousepos.x - rectHandle.x
        event.Skip()

    def _OnMouseMotion(self, event):
        if event.Dragging() and event.LeftIsDown() and self.HasCapture():
            x, y, w, h = self.GetRect()
            xmouse, ymouse = event.GetPosition()
            oldvalue = self.value
            #~ self.value = int(round((xmouse-self.xdelta-self.xo+self.wH/2) * (self.maxValue - self.minValue) / float(w-2*self.xo)))
            #~ self.value = max(min(self.value, self.maxValue), self.minValue)
            self.SetValue(int(round((xmouse-self.xdelta-self.xo+self.wH/2) * (self.maxValue - self.minValue) / float(w-2*self.xo))))
            if self.value != oldvalue:
                self._SendScrollEvent()
            #~ dc = wx.BufferedDC(wx.ClientDC(self))
            #~ dc.Clear()
            #~ self._PaintSlider(dc)

    def _OnLeftUp(self, event):
        self.isclicked = False
        self.xdelta = None
        if self.HasCapture():
            self.ReleaseMouse()
            self._SendScrollEndEvent()
            dc = wx.BufferedDC(wx.ClientDC(self))
            dc.Clear()
            self._PaintSlider(dc)
        else:
            # If clicked on a bookmark, go to that frame
            mousepos = event.GetPosition()
            index = self.HitTestBookmark(mousepos)
            if index is not None:
                self.SetValue(self.bookmarks[index][0])
                self._SendScrollEndEvent()
            #~ # If clicked on a selection button, create the selection bookmark
            #~ bmtype = self.HitTestSelectionButton(mousepos)
            #~ if bmtype is not None:
                #~ if self.bookmarks.count((self.value, bmtype)) == 0:
                    #~ self.SetBookmark(self.value, bmtype)
                #~ else:
                    #~ self.RemoveBookmark(self.value, bmtype)
        event.Skip()

    def _OnMouseWheel(self, event):
        #~ if event.LeftIsDown():
        if self.HasCapture():
            if event.GetWheelRotation() > 0:
                delta = -1
            else:
                delta = 1
            oldvalue = self.value
            self.SetValue(self.value+delta)
            if self.value != oldvalue:
                self._SendScrollEvent()

    def _OnKeyDown(self, event):
        if self.HasCapture():
            key = event.GetKeyCode()
            oldvalue = self.value
            if key in (wx.WXK_LEFT, wx.WXK_UP):
                self.SetValue(self.value-1)
            elif key in (wx.WXK_RIGHT, wx.WXK_DOWN):
                self.SetValue(self.value+1)
            if self.value != oldvalue:
                self._SendScrollEvent()

    def _SendScrollEvent(self):
        event = wx.CommandEvent(wx.wxEVT_SCROLL_THUMBTRACK, self.GetId())
        event.SetEventObject(self)
        self.GetEventHandler().ProcessEvent(event)

    def _SendScrollEndEvent(self):
        event = wx.CommandEvent(wx.wxEVT_SCROLL_ENDSCROLL, self.GetId())
        event.SetEventObject(self)
        self.GetEventHandler().ProcessEvent(event)

    def _OnSize(self, event):
        dc = wx.BufferedDC(wx.ClientDC(self))
        dc.Clear()
        self._PaintSlider(dc)

    def _OnPaint(self, event):
        # Color info
        self._DefineBrushes()
        dc = wx.PaintDC(self)
        #~ dc = wx.BufferedPaintDC(self)
        self._PaintSlider(dc)

    def _PaintSlider(self, dc):
        boolEnabled = self.IsEnabled()
        # Paint the bar
        x, y = (0, 0)
        w, h = self.GetSize()
        xB, yB, wB, hB = self.xo, self.yo, w-2*self.xo, h-self.yo-self.yo2
        xH, yH, wH, hH = -1, self.yo-3, self.wH, hB+6
        # First paint background
        dc.SetPen(self.penWindowBackground)
        dc.SetBrush(self.brushWindowBackground)
        dc.DrawRectangle(0, 0, w, h)
        dc.SetPen(self.penBackground)
        dc.SetBrush(self.brushBackground)
        dc.DrawRectangle(xB, yB, wB, hB)
        # Then paint the bookmark selections
        if self.selections is not None:
            if boolEnabled:
                dc.SetPen(wx.Pen(wx.BLUE))
                dc.SetBrush(wx.BLUE_BRUSH)
            else:
                color = wx.Colour(200,200,230)
                dc.SetPen(wx.Pen(color))
                dc.SetBrush(wx.Brush(color))
            for start, stop in self.selections:
                start = min(max(start, self.minValue), self.maxValue)
                stop = min(max(stop, self.minValue), self.maxValue)
                pixelstart = int(start * wB / float(self.maxValue - self.minValue)) + self.xo
                pixelstop = int(stop * wB / float(self.maxValue - self.minValue)) + self.xo
                dc.DrawRectangle(pixelstart, yB, pixelstop - pixelstart, hB)
        # Then draw the bookmark triangles
        dc.SetPen(self.penWindowBackground)
        if boolEnabled:
            dc.SetBrush(wx.BLACK_BRUSH)
        else:
            dc.SetBrush(self.brushGrayText)
        wT = self.wT
        for value, bmtype in self.bookmarks:
            if value > self.maxValue or value < self.minValue:
                continue
            pixelpos = int(value * wB / float(self.maxValue - self.minValue)) + self.xo
            p1 = wx.Point(pixelpos, h-wT/2)
            if bmtype == 0:
                if value in self.bookmarkDict:                    
                    dc.SetBrush(wx.BLUE_BRUSH)
                else:
                    dc.SetBrush(wx.BLACK_BRUSH)
                p2 = wx.Point(pixelpos-wT/4, h)
                p3 = wx.Point(pixelpos+wT/4, h)
                dc.DrawPolygon((p1, p2, p3))
            elif bmtype == 1:
                p2 = wx.Point(pixelpos-wT/2, h)
                p3 = wx.Point(pixelpos, h)
                dc.DrawPolygon((p1, p2, p3))
                dc.SetPen(wx.BLACK_PEN)
                dc.DrawLine(pixelpos, h-1, pixelpos+wT/4, h-1)
                dc.SetPen(self.penWindowBackground)
            elif bmtype == 2:
                p2 = wx.Point(pixelpos, h)
                p3 = wx.Point(pixelpos+wT/2, h)
                dc.DrawPolygon((p1, p2, p3))
                dc.SetPen(wx.BLACK_PEN)
                dc.DrawLine(pixelpos, h-1, pixelpos-wT/4, h-1)
                dc.SetPen(self.penWindowBackground)
        # Then paint the border
        dc.SetPen(self.penShadow)
        dc.DrawLine(xB, yB, xB+wB, yB)
        dc.DrawLine(xB, yB, xB, yB+hB)
        dc.SetPen(self.penDarkShadow)
        dc.DrawLine(xB+1, yB+1, xB+wB, yB+1)
        dc.DrawLine(xB+1, yB+1, xB+1, yB+hB)
        dc.SetPen(self.penHighlight2)
        dc.DrawLine(xB+wB, yB, xB+wB, yB+hB)
        dc.DrawLine(xB, yB+hB, xB+wB+1, yB+hB)
        dc.SetPen(self.penHighlight)
        dc.DrawLine(xB+wB-1, yB+1, xB+wB-1, yB+hB)
        dc.DrawLine(xB+1, yB+hB-1, xB+wB, yB+hB-1)
        # Then paint the handle
        pixelpos = int(self.value * wB / float(self.maxValue - self.minValue)) + self.xo
        pixelpos0 = pixelpos - self.wH/2
        if self.isclicked or not boolEnabled:
            dc.SetPen(self.penHandle2)
            dc.SetBrush(self.brushHandle2)
        else:
            dc.SetPen(self.penHandle)
            dc.SetBrush(self.brushHandle)
        dc.DrawRectangle(pixelpos0, yH, wH, hH)
        dc.SetPen(self.penHighlight2)
        dc.DrawLine(pixelpos0, yH, pixelpos0+wH, yH)
        dc.DrawLine(pixelpos0, yH, pixelpos0, yH+hH)
        dc.SetPen(self.penDarkShadow)
        dc.DrawLine(pixelpos0+wH, yH, pixelpos0+wH, yH+hH)
        dc.DrawLine(pixelpos0, yH+hH, pixelpos0+wH+1, yH+hH)
        dc.SetPen(self.penShadow)
        dc.DrawLine(pixelpos0+wH-1, yH+1, pixelpos0+wH-1, yH+hH)
        dc.DrawLine(pixelpos0+1, yH+hH-1, pixelpos0+wH, yH+hH-1)
        if self.selmode == 1:
            hH2 = hH/2
            border = 3
            yH2 = yB #yH + hH/4
            for bmtype in (1,2):
                if bmtype == 1:
                    xpos = pixelpos0 - self.wH
                    p1 = wx.Point(xpos+border, yH2+hH2-border)
                    p2 = wx.Point(xpos+self.wH-border, yH2+hH2-border)
                    p3 = wx.Point(xpos+self.wH-border, yH2+border)
                else:
                    xpos = pixelpos0 + self.wH #+ 1
                    p1 = wx.Point(xpos+border, yH2+border)
                    p2 = wx.Point(xpos+border, yH2+hH2-border)
                    p3 = wx.Point(xpos+self.wH-border, yH2+hH2-border)
                # Draw the button
                dc.SetPen(self.penHandle)
                dc.SetBrush(self.brushHandle)
                dc.DrawRectangle(xpos, yH2, self.wH, hH2)
                dc.SetPen(self.penHighlight2)
                dc.DrawLine(xpos, yH2, xpos+wH, yH2)
                dc.DrawLine(xpos, yH2, xpos, yH2+hH2)
                dc.SetPen(self.penDarkShadow)
                if bmtype == 2:
                    dc.DrawLine(xpos+wH, yH2, xpos+wH, yH2+hH2)
                    dc.DrawLine(xpos, yH2+hH2, xpos+wH+1, yH2+hH2)
                else:
                    dc.DrawLine(xpos, yH2+hH2, xpos+wH, yH2+hH2)
                dc.SetPen(self.penShadow)
                dc.DrawLine(xpos+wH-1, yH2+1, xpos+wH-1, yH2+hH2)
                dc.DrawLine(xpos+1, yH2+hH2-1, xpos+wH, yH2+hH2-1)
                # Draw the button image
                if boolEnabled:
                    dc.SetPen(wx.BLACK_PEN)
                    dc.SetBrush(wx.BLACK_BRUSH)
                else:
                    dc.SetPen(self.penGrayText)
                    dc.SetBrush(self.brushGrayText)
                dc.DrawPolygon((p1, p2, p3))


    def _createSelections(self):
        selectionList = []
        start = stop = None
        #~ selectionmarks = self.bookmarks
        selectionmarks = [item for item in self.bookmarks if item[1] != 0]
        selectionmarks.sort()
        if len(selectionmarks) == 0:
            return None
        if selectionmarks[0][1] == 2:
            start =self.minValue
        for value, bmtype in selectionmarks:
            if start is None:
                if bmtype == 1:
                    start = value
            else:
                if bmtype == 2:
                    stop = value
                    selectionList.append((start, stop))
                    start = stop =None
        if start is not None:
            stop = self.maxValue
            selectionList.append((start, stop))
        return selectionList

    def _getRectHandle(self):
        x, y, w, h = self.GetRect()
        pixelpos = int(self.value * (w-2*self.xo) / float(self.maxValue - self.minValue))
        rectHandle = wx.Rect(pixelpos-self.wH/2+self.xo, self.yo-3, self.wH, h-self.yo-self.yo2+6)
        return rectHandle

    def GetValue(self):
        return self.value

    def GetMax(self):
        return self.minValue

    def GetMax(self):
        return self.maxValue

    def SetValue(self, value):
        self.value = max(min(value, self.maxValue), self.minValue)
        dc = wx.BufferedDC(wx.ClientDC(self))
        dc.Clear()
        self._PaintSlider(dc)
        return True

    def SetRange(self, minValue, maxValue):
        if minValue >= maxValue:
            if minValue == 0 and (maxValue == -1 or maxValue ==0):
                maxValue = 1
            else:
                print>>sys.stderr, _('Error: minValue must be less than maxValue')
                return
        self.minValue = minValue
        self.maxValue = maxValue
        self.selections = self._createSelections()
        dc = wx.BufferedDC(wx.ClientDC(self))
        dc.Clear()
        self._PaintSlider(dc)
        return True

    def SetBookmark(self, value, bmtype=0, refresh=True):
        # Type=0: bookmark, Type=1: selection start, Type=2: selection end
        #~ if value >= self.minValue and value <= self.maxValue and bmtype in (0, 1, 2) and self.bookmarks.count((value, bmtype)) == 0:
        if bmtype in (0, 1, 2) and self.bookmarks.count((value, bmtype)) == 0:
            try:
                index = [item[0] for item in self.bookmarks].index(value)
                self.bookmarks[index] = (value, bmtype)
            except ValueError:
                self.bookmarks.append((value, bmtype))
            if refresh:
                if self.bookmarks:
                    self.selections = self._createSelections()
                else:
                    self.selections = None
                dc = wx.BufferedDC(wx.ClientDC(self))
                dc.Clear()
                self._PaintSlider(dc)
            return True
        else:
            return False

    def RemoveBookmark(self, value, bmtype=0, refresh=True):
        try:
            self.bookmarks.remove((value, bmtype))
            if refresh:
                if self.bookmarks:
                    self.selections = self._createSelections()
                else:
                    self.selections = None
                dc = wx.BufferedDC(wx.ClientDC(self))
                dc.Clear()
                self._PaintSlider(dc)
            return True
        except ValueError:
            return False

    def RemoveAllBookmarks(self):
        if self.bookmarks:
            self.bookmarks = []
            self.selections = None
            dc = wx.BufferedDC(wx.ClientDC(self))
            dc.Clear()
            self._PaintSlider(dc)
        return True

    def GetBookmarks(self):
        return self.bookmarks[:]

    def GetSelections(self):
        if self.selections:
            return self.selections[:]
        else:
            return self.selections

    def ToggleSelectionMode(self, mode=0):
        if self.selmode == 0 or mode == 1:
            self.selmode = 1
        else:
            self.selmode = 0
        dc = wx.BufferedDC(wx.ClientDC(self))
        dc.Clear()
        self._PaintSlider(dc)

    def HitTestHandle(self, mousepos):
        #~ x, y, w, h = self.GetRect()
        #~ pixelpos = int(self.value * (w-2*self.xo) / float(self.maxValue - self.minValue))
        #~ rectHandle = wx.Rect(pixelpos-self.wH/2+self.xo, self.yo-3, self.wH, h-self.yo-self.yo2+6)
        #~ return rectHandle.Inside(mousepos)
        rectHandle = self._getRectHandle()
        return rectHandle.Inside(mousepos)

    def HitTestBookmark(self, mousepos):
        x, y, w, h = self.GetRect()
        hitlist = []
        index = 0
        for value, bmtype in self.bookmarks:
            pixelpos = int(value * (w-2*self.xo) / float(self.maxValue - self.minValue)) + self.xo
            wT = self.wT
            if bmtype == 0:
                rect = wx.Rect(pixelpos-wT/4, h-self.yo2, wT/2, wT/2)
            elif bmtype == 1:
                rect = wx.Rect(pixelpos-wT/2, h-self.yo2, wT/2+wT/4, wT/2)
            elif bmtype == 2:
                rect = wx.Rect(pixelpos-wT/4, h-self.yo2, wT/2+wT/4, wT/2)
            if rect.Inside(mousepos):
                hitlist.append((value, pixelpos, index))
            index += 1
        if hitlist:
            if len(hitlist) == 1:
                index = hitlist[0][2]
                #~ self.SetValue(hitlist[0][0])
            else:
                index = min([(abs(pixelpos-mousepos.x), index) for value, pixelpos, index in hitlist])[1]
                #~ value = min([(abs(pixelpos-mousepos.x), value) for value, pixelpos, index in hitlist])[1]
                #~ self.SetValue(value)
            return index
        else:
            return None

    def HitTestSelectionButton(self, mousepos):
        if self.selmode == 1:
            x, y, w, h = self.GetRect()
            pixelpos = int(self.value * (w-2*self.xo) / float(self.maxValue - self.minValue))
            rectLeftButton = wx.Rect(pixelpos-self.wH/2+self.xo-self.wH, self.yo-3, self.wH, (h-self.yo-self.yo2+6)/1)
            rectRightButton = wx.Rect(pixelpos-self.wH/2+self.xo+self.wH, self.yo-3, self.wH, (h-self.yo-self.yo2+6)/1)
            bmtype = None
            if rectLeftButton.Inside(mousepos):
                bmtype = 1
            if rectRightButton.Inside(mousepos):
                bmtype = 2
            return bmtype

    def _HitTestHandleDeadZone(self, mousepos):
        rectHandle = self._getRectHandle()
        rectHandle.Inflate(3*self.wH, 0)
        return rectHandle.Inside(mousepos)

# Main program window
class MainFrame(wxp.Frame):
    # Initialization functions
    def __init__(self, parent=None, id=wx.ID_ANY, title='AvsPmod', pos=wx.DefaultPosition, size=(700, 550), style=wx.DEFAULT_FRAME_STYLE):
        wxp.Frame.__init__(self, parent, id, pos=pos, size=size, style=style)
        self.version = version
        self.firsttime = False
        pyavs.InitRoutines()
        # Define program directories
        if hasattr(sys,'frozen'):
            self.programdir = os.path.dirname(sys.executable)
        else:
            self.programdir = os.path.abspath(os.path.dirname(sys.argv[0]))
        if type(self.programdir) != unicode:
            self.programdir = unicode(self.programdir, encoding)
        self.toolsfolder = os.path.join(self.programdir, 'tools')
        sys.path.insert(0, self.toolsfolder)
        self.macrofolder = os.path.join(self.programdir, 'macros')
        # Get persistent options
        self.optionsfilename = os.path.join(self.programdir, 'options.dat')
        self.filterdbfilename = os.path.join(self.programdir, 'filterdb.dat')
        self.lastSessionFilename = os.path.join(self.programdir, '_last_session_.ses')
        self.getOptionsDict()        
        self.IdleCall = []
        self.defineFilterInfo()
        
        # load translation file
        self.translations_dir = 'translations'
        self.options['lang'] = self.options.get('lang', 'eng') # remove this line later
        if self.options['lang'] != 'eng':
            sys.path.append(self.translations_dir)
            sys.dont_write_bytecode = True
            try:
                translation = __import__('translation_' + self.options['lang'])
            except ImportError:
                translation = None
            else:
                try:
                    global messages
                    messages = translation.messages
                except AttributeError:
                    pass
            finally:
                sys.dont_write_bytecode = False
        
        # single-instance socket
        self.port = 50009
        self.instance = wx.SingleInstanceChecker(title+wx.GetUserId())
        self.boolSingleInstance = self.options.setdefault('singleinstance', False)
        if self.boolSingleInstance:
            #~ self.port = 50009
            #~ self.instance = wx.SingleInstanceChecker(title+wx.GetUserId())
            if self.instance.IsAnotherRunning():
                # Send data to the main instance via socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(('localhost', self.port))
                pickledstring = StringIO.StringIO()
                cPickle.dump(sys.argv[1:],pickledstring)
                sock.sendall(pickledstring.getvalue())
                response = sock.recv(8192)
                self.Destroy()
                return None
            else:
                def OnArgs(evt):
                    self.ProcessArguments(evt.data)
                self.Bind(wxp.EVT_POST_ARGS, OnArgs)
                # Start socket server (in a separate thread) to receive arguments from other instances
                self.argsPosterThread = wxp.ArgsPosterThread(self)
                self.argsPosterThread.Start()
        else:
            if self.instance.IsAnotherRunning():
                self.options['exitstatus'] = 0

        self.optionsDlgInfo = self.getOptionsDlgInfo()
        #~ if self.options['helpdir'].count('%programdir%') > 0:
            #~ self.options['helpdir'] = self.options['helpdir'].replace('%programdir%', self.programdir)
        self.options['helpdir'] = self.options['helpdir'].replace('%programdir%', self.programdir)
        # Program size and position options
        self.separatevideowindow = self.options['separatevideowindow']
        dimensions = self.options.get('dimensions')
        if dimensions is not None and dimensions[0] > 0 and dimensions[1] > 0:
            self.SetDimensions(*dimensions)
            # Move the window if it's offscreen
            size = self.GetSize()
            pos = self.GetPosition()
            wC, hC = wx.ScreenDC().GetSize()
            # if (pos[0]+size[0]>wC) or (pos[1]+size[1]>hC):
            if (pos[0]+50>wC) or (pos[1]+50>hC):
                #~ self.Center()
                pass
        else:
            #~ self.Center()
            pass
        if self.options['alwaysontop']:
            style = wx.DEFAULT_FRAME_STYLE|wx.STAY_ON_TOP
        else:
            style = wx.DEFAULT_FRAME_STYLE
        self.SetWindowStyle(style)
        # Drag-and-drop target for main window
        class MainFrameDropTarget(wx.PyDropTarget):
            def __init__(self, win):
                wx.PyDropTarget.__init__(self)
                self.win = win
                self.textdata = wx.TextDataObject()
                self.filedata = wx.FileDataObject()
                self.data = wx.DataObjectComposite()
                self.data.Add(self.textdata)
                self.data.Add(self.filedata)
                self.SetDataObject(self.data)

            def OnData(self, x, y, default):
                self.GetData()
                if self.textdata.GetTextLength() > 1:
                    text = self.textdata.GetText()
                    self.textdata.SetText('')
                    self.win.NewTab(copyselected=False)
                    self.win.currentScript.SetText(text)
                    self.win.currentScript.SelectAll()
                else:
                    for filename in self.filedata.GetFilenames():
                        self.win.OpenFile(filename=filename)
                return False

        class ScriptDropTarget(wx.DropTarget):
            def __init__(self, win, app):
                wx.PyDropTarget.__init__(self)
                self.win = win
                self.app = app
                self.textdata = wx.TextDataObject()
                self.filedata = wx.FileDataObject()
                self.data = wx.DataObjectComposite()
                self.data.Add(self.textdata)
                self.data.Add(self.filedata)
                self.SetDataObject(self.data)
                self.oldPos = None

            def OnLeave(self):
                self.win.SetCaretWidth(1)

            def OnDragOver(self, x, y, default):
                point = wx.Point(x,y)
                textPos = self.win.PositionFromPoint(point)
                textPoint = self.win.PointFromPosition(textPos)
                if textPos != self.oldPos:
                    self.win.SetCaretWidth(0)
                    self.win.Refresh()
                dc = wx.ClientDC(self.win)
                dc.SetPen(wx.Pen('black', 1))
                dc.DrawLine(
                    textPoint.x,
                    textPoint.y,
                    textPoint.x,
                    textPoint.y + self.win.TextHeight(0)
                )
                self.oldPos = textPos
                return wx.DragMove

            def OnData(self, x, y, default):
                script = self.win
                script.SetCaretWidth(1)
                self.GetData()
                if self.textdata.GetTextLength() > 1:
                    # Get the clipboard data
                    text = self.textdata.GetText()
                    self.textdata.SetText('')
                    # Get the current selection positions
                    posA, posB = script.GetSelection()
                    # Go to the current mouse position
                    point = wx.Point(x,y)
                    textPos = script.PositionFromPoint(point)
                    script.GotoPos(textPos)
                    # Erase the old selection
                    script.SetTargetStart(posA)
                    script.SetTargetEnd(posB)
                    script.ReplaceTarget('')
                    # Insert the clipboard text in the current position
                    curPos = script.GetCurrentPos()
                    script.InsertText(curPos, text)
                    script.SetSelection(curPos, curPos+len(text))
                else:
                    # Go to the current mouse position
                    point = wx.Point(x,y)
                    textPos = script.PositionFromPoint(point)
                    script.GotoPos(textPos)
                    filenames = self.filedata.GetFilenames()
                    if len(filenames) == 1 and os.path.splitext(filenames[0])[1].lower() not in ('.avs', '.avsi', '.ses'):
                        # Insert the single filename as a source
                        self.app.InsertSource(filenames[0])
                    else:
                        # Open each filename as a script
                        for filename in self.filedata.GetFilenames():
                            self.app.OpenFile(filename=filename)
                return True

        self.SetDropTarget(MainFrameDropTarget(self))
        self.scriptDropTarget = ScriptDropTarget
        # Create all the program's controls and dialogs
        self.NewFileName = _('New File')
        self.scrapWindow = ScrapWindow(self)
        self.bookmarkDict = {}
        self.recentframes = []
        self.bmpVideo = None
        self.createWindowElements()
        if not __debug__:
            sys.stdout = self.scrapWindow
        if not self.separatevideowindow:
            cropdialogparent = self
        else:
            cropdialogparent = self.videoDialog
        self.cropDialog = self.createCropDialog(cropdialogparent)
        self.trimDialog = self.createTrimDialog(cropdialogparent)
        # Internal class variables
        self.name = title
        self.currentframenum = None
        self.zoomfactor = 1
        self.zoomwindow = False
        self.zoomwindowfit = False
        self.zoomwindowfill = False
        #~ self.currentScript = None
        self.lastcrop = ""
        self.oldWidth = 0
        self.oldHeight = 0
        self.oldFramecount = None
        self.oldPreviewtxt = None
        self.oldLastSplitVideoPos = None
        self.oldLastSplitSliderPos = None
        self.oldSliderWindowShown = None
        self.oldBoolSliders = None
        self.xo = self.yo = 5
        self.sliderOpenString = '[<'
        self.sliderCloseString = '>]'
        self.fc = None
        self.regexp = re.compile(r'\%s.*?\%s' % (self.sliderOpenString, self.sliderCloseString))
        self.cropValues = {
            'left': 0,
            'top': 0,
            '-right': 0,
            '-bottom': 0,
        }
        self.oldCropValues = self.cropValues
        self.middleDownScript = False
        self.refreshAVI = True
        self.lastshownframe = None
        self.paintedframe = None
        self.oldlinenum = None
        self.dlgAvs2avi = None
        #~ self.tab_processed = False
        self.macroVars = {'last': None}
        self.imageFormats = {
            '.bmp': (_('Windows Bitmap (*.bmp)'), wx.BITMAP_TYPE_BMP),
            '.gif': (_('Animation (*.gif)'), wx.BITMAP_TYPE_GIF),
            '.jpg': (_('JPEG (*.jpg)'), wx.BITMAP_TYPE_JPEG),
            '.pcx': (_('Zsoft Paintbrush (*.pcx)'), wx.BITMAP_TYPE_PCX),
            '.png': (_('Portable Network Graphics (*.png)'), wx.BITMAP_TYPE_PNG),
            '.pnm': (_('Netpbm (*.pnm)'), wx.BITMAP_TYPE_PNM),
            '.tif': (_('Tagged Image File (*.tif)'), wx.BITMAP_TYPE_TIF),
            '.xpm': (_('ASCII Text Array (*.xpm)'), wx.BITMAP_TYPE_XPM),
            '.ico': (_('Windows Icon (*.ico)'), wx.BITMAP_TYPE_ICO),
        }
        self.markFrameInOut = self.options['trimmarkframes']
        if self.options['trimreversechoice'] == 0:
            self.invertSelection = False
        else:
            self.invertSelection = True
        if self.options['videostatusbarinfo'] == None:
            self.videoStatusBarInfo = _('Frame') + ' %F / %FC  -  (%T)      %POS  %HEX \t\t %Z %Wx%H (%AR)  -  %FR ' + _('fps') + '  -  %CS'
        else:
            self.videoStatusBarInfo = self.options['videostatusbarinfo']
        self.videoStatusBarInfoParsed, self.showVideoPixelInfo, self.showVideoPixelAvisynth = self.ParseVideoStatusBarInfo(self.videoStatusBarInfo)
        self.foldAllSliders = True
        self.matrix = 'Rec601'
        self.interlaced = self.swapuv = False
        self.flip = []
        self.titleEntry = None
        # Events
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnNotebookPageChanged)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGING, self.OnNotebookPageChanging)
        #~ self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClickWindow)

        if not self.separatevideowindow:
            def OnSize(event):
                if self.zoomwindowfit and self.previewWindowVisible:
                    #~ self.IdleCall = (self.ShowVideoFrame, tuple(), {'forceRefresh': True, 'focus': False})
                    self.IdleCall.append((self.ShowVideoFrame, tuple(), {'focus': False}))
                if self.titleEntry:
                    self.scriptNotebook.SetFocus()
                event.Skip()
            self.Bind(wx.EVT_SIZE, OnSize)
        else:
            def OnSize(event):
                if self.zoomwindow and self.previewWindowVisible:
                    #~ self.IdleCall = (self.ShowVideoFrame, tuple(), {'forceRefresh': True, 'focus': False})
                    self.IdleCall.append((self.ShowVideoFrame, tuple(), {'focus': False}))
                event.Skip()
            self.videoDialog.Bind(wx.EVT_SIZE, OnSize)

        # Command line arguments
        self.UpdateRecentFilesList()
        curdir = os.getcwd()
        self.reloadList = None
        if self.options['exitstatus']:
            self.IdleCall.append((wx.MessageBox, (_('A crash detected at the last running!'), _('Warning'), wx.OK|wx.ICON_EXCLAMATION, self), {})) 
        if self.options['startupsession'] or self.options['exitstatus']:
            if self.options['alwaysloadstartupsession'] or len(sys.argv) <= 1 or not self.options['promptexitsave'] or self.options['exitstatus']:
                if os.path.exists(self.lastSessionFilename):
                    self.LoadSession(self.lastSessionFilename, saverecentdir=False, resize=False, backup=True, startup=True)
        if not self.options['exitstatus']:
            self.options['exitstatus'] = 1
            f = open(self.optionsfilename, mode='wb')
            cPickle.dump(self.options, f, protocol=0)
            f.close()
        if len(sys.argv)>1:
            self.ProcessArguments(sys.argv[1:])
        #~ if not self.currentScript.sliderWindowShown:
            #~ self.HideSliderWindow(self.currentScript)
        #~ else:
            #~ newSliderWindow.Show()
            #~ self.ShowSliderWindow(self.currentScript)

        if self.previewWindowVisible:
            #~ self.HidePreviewWindow()
            self.need_to_show_preview = True
        else:
            self.need_to_show_preview = False
        # Misc
        self.SetProgramTitle()
        self.SetIcon(AvsP_icon.getIcon())

        if self.separatevideowindow:
            def OnActivate(event):
                if event.GetActive():
                    self.currentScript.SetFocus()
                event.Skip()
            self.Bind(wx.EVT_ACTIVATE, OnActivate)


        def OnMove(event):
            self.currentScript.UpdateCalltip()
        self.Bind(wx.EVT_MOVE, OnMove)

        #~ self.firsttime = False
        self.doMaximize = False
        def _x_OnIdle(event):
            if self.doMaximize:
                if self.options.get('maximized'):
                    self.Maximize(True)
                if self.options.get('maximized2') and self.separatevideowindow:
                    self.videoDialog.Maximize(True)
                index = self.scriptNotebook.GetSelection()
                self.ReloadModifiedScripts()
                self.scriptNotebook.SetSelection(index)
                self.currentScript.SetFocus()
                self.doMaximize = False
            if not self.firsttime:
                if self.separatevideowindow:
                    self.Show()
                vidmenu = self.videoWindow.contextMenu
                menu = vidmenu.FindItemById(vidmenu.FindItem(_('&Zoom'))).GetSubMenu()
                menuItem = menu.FindItemByPosition(self.options['zoomindex'])
                if menuItem is not None:
                    self.OnMenuVideoZoom(None, menuItem=menuItem, show=False)
                if self.need_to_show_preview:
                    self.ShowVideoFrame(self.startupframe, forceRefresh=False)
                self.Refresh()
                if self.mainSplitter.IsSplit():
                    self.SplitVideoWindow()
                    #~ self.SplitVideoWindow(forcefit=True)
                    #~ self.lastSplitVideoPos = None
                self.Show()
                self.firsttime = True
                self.doMaximize = True
        #~ self.IdleCall = None
        def OnIdle(event):
            if self.IdleCall:
                func, args, kwargs = self.IdleCall.pop()
                func(*args, **kwargs)
                #~ self.IdleCall = None
        self.Bind(wx.EVT_IDLE, OnIdle)

        # Display the program
        if self.separatevideowindow:
            self.Show()
        vidmenu = self.videoWindow.contextMenu
        menu = vidmenu.FindItemById(vidmenu.FindItem(_('&Zoom'))).GetSubMenu()
        menuItem = menu.FindItemByPosition(self.options['zoomindex'])
        if menuItem is not None:
            self.OnMenuVideoZoom(None, menuItem=menuItem, show=False)
        if self.need_to_show_preview:
            #~ self.ShowVideoFrame(self.startupframe, forceRefresh=False)
            self.IdleCall.append((self.ShowVideoFrame, (self.startupframe,), {'forceRefresh':False}))
        #~ self.Refresh()
        if self.mainSplitter.IsSplit():
            self.SplitVideoWindow()
        self.Show()
        if self.options.get('maximized'):
            self.Maximize(True)
        if self.options.get('maximized2') and self.separatevideowindow:
            self.videoDialog.Maximize(True)
        index = self.scriptNotebook.GetSelection()
        self.ReloadModifiedScripts()
        self.scriptNotebook.SetSelection(index)
        self.currentScript.SetFocus()
        
        # Update the translation file if necessary
        if self.options['lang'] != 'eng':
            if translation:
                try:
                    try:
                        translation_version = translation.version
                    except AttributeError:
                        translation_version = None
                    if translation_version != version:
                        if self.UpdateTranslationFile():
                            wx.MessageBox(_('%s translation file updated with new messages to translate') 
                                            % self.options['lang'], _('Translation updated'))
                        else:
                            wx.MessageBox(_('%s translation file updated.  No new messages to translate.') 
                                            % self.options['lang'], _('Translation updated'))
                except NameError, err:
                    pass
            else:
                wx.MessageBox(_("%s language couldn't be loaded") % self.options['lang'], 
                              _('Error'), style=wx.OK|wx.ICON_ERROR)
                self.options['lang'] = 'eng'
    
    def ProcessArguments(self, args):
        if args:
            self.HidePreviewWindow()
            for arg in args:
                arg = arg.decode(encoding)
                if os.path.exists(arg):
                    if os.path.dirname(arg) == '':
                        arg = os.path.join(os.getcwd(), arg)
                    self.OpenFile(filename=arg) # BUG: sys.argv gives back short filenames only?!!
                    self.currentScript.GotoPos(0)
                    self.currentScript.EnsureCaretVisible()

    def getOptionsDict(self):
        boolMakeOptions = True
        oldOptions = None
        if os.path.exists(self.optionsfilename):
            f = open(self.optionsfilename, mode='rb')
            oldOptions = cPickle.load(f)
            f.close()
            oldVersion = oldOptions.get('version')
            if oldVersion.startswith('1.'):
                oldOptions = None
            elif oldVersion == self.version:
                self.options = oldOptions
                boolMakeOptions = False
        if boolMakeOptions or __debug__:
            templateDict = {
                'avi': 'AVISource(***)',
                'wav': 'WAVSource(***)',
                'd2v': 'MPEG2Source(***, cpu=0)',
                'dga': 'AVCSource(***)',
                'mpg': 'DirectShowSource(***)',
                'mp4': 'DirectShowSource(***)',
                'mkv': 'DirectShowSource(***)',
                'wmv': 'DirectShowSource(***)',
                'avs': 'Import(***)',
                'dll': 'LoadPlugin(***)',
                'bmp': 'ImageReader(***)',
                'jpg': 'ImageReader(***)',
                'png': 'ImageReader(***)',
            }
            textstylesDict = {
                'default': 'face:Verdana,size:10,fore:#000000,back:#FFFFFF',
                'comment': 'face:Comic Sans MS,size:9,fore:#007F00,back:#FFFFFF',
                'number': 'face:Verdana,size:10,fore:#007F7F,back:#FFFFFF',
                'operator': 'face:Verdana,size:10,fore:#000000,back:#FFFFFF,bold',
                'string': 'face:Courier New,size:10,fore:#7F007F,back:#FFFFFF',
                'stringtriple': 'face:Courier New,size:10,fore:#7F0000,back:#FFFFFF',
                'stringeol': 'face:Courier New,size:10,fore:#000000,back:#E0C0E0',
                'internalfilter': 'face:Verdana,size:10,fore:#00007F,back:#FFFFFF,bold',
                'externalfilter': 'face:Verdana,size:10,fore:#0080C0,back:#FFFFFF,bold',
                'clipproperty': 'face:Verdana,size:10,fore:#00007F,back:#FFFFFF',
                'userdefined': 'face:Verdana,size:10,fore:#8000FF,back:#FFFFFF,bold',
                'userslider': 'face:Arial,size:10,fore:#00007F,back:#FFFFFF',
                'monospaced': 'face:Courier New,size:10',
                'internalfunction': 'face:Verdana,size:10,fore:#007F7F,back:#FFFFFF',
                'keyword': 'face:Verdana,size:10,fore:#400080,back:#FFFFFF,bold',
                'miscword': 'face:Verdana,size:10,fore:#00007F,back:#FFFFFF,bold',
                'calltip': 'fore:#808080,back:#FFFFFF',
                'calltiphighlight': 'fore:#000000',
                'bracelight': 'face:Verdana,size:10,fore:#0000FF,back:#FFFFFF,bold',
                'badbrace': 'face:Verdana,size:10,fore:#FF0000,back:#FFFFFF,bold',
                'badnumber': 'face:Verdana,size:10,fore:#FF0000,back:#FFFFFF',
                'linenumber': 'face:Verdana,fore:#555555,back:#C0C0C0',
                'datatype': 'face:Verdana,size:10,fore:#0000FF,back:#FFFFFF',
                'cursor': 'fore:#000000',
                'highlight': 'back:#C0C0C0',                
                'highlightline': 'back:#E8E8FF',
                'scrapwindow': 'face:Comic Sans MS,size:10,fore:#0000AA,back:#F5EF90',
            }
            # Create the options dict
            self.options = {
                # INTERNAL OPTIONS
                'templates': templateDict,
                'textstyles': textstylesDict,
                #~ 'avskeywords': avsKeywords,
                #~ 'avsoperators': avsOperators,
                #~ 'avsdatatypes': avsDatatypes,
                #~ 'avsmiscwords': [],
                'filteroverrides': {},
                'filterpresets': {},
                'filterdb': {},
                'autcompletetypeflags': [True,True,True,True,True],
                'filterremoved': set(),
                'shortcuts': [],
                'recentdir': '',
                'recentdirPlugins': '',
                'recentdirSession': '',
                'recentfiles': None,
                #~ 'lasthelpdir': None,
                'scraptext': ('', 0, 0),
                'maximized': False,
                'maximized2': False,
                'dimensions': (50, 50, 700, 550),
                'cropchoice': 0,
                'triminsertchoice': 0,
                'trimreversechoice': 0,
                'trimmarkframes': True,
                'imagechoice': 0,
                'imagenameformat': '%s%06d',
                'imagesavedir': '',
                'zoomindex': 2,
                'exitstatus': 0,
                'reservedshortcuts': ['Tab', 'Shift+Tab', 'Ctrl+Z', 'Ctrl+Y', 'Ctrl+X', 'Ctrl+C', 'Ctrl+V', 'Ctrl+A'],
                # GENERAL OPTIONS
                'helpdir': r'%programdir%\help',
                'avisynthdir': '',
                'avisynthhelpfile': r'%avisynthdir%\docs\english\index.htm',
                'externalplayer': '',
                'externalplayerargs': '',
                'docsearchpaths': r'%avisynthdir%\plugins; %avisynthdir%\docs\english\corefilters; %avisynthdir%\docs\english\externalfilters;',
                'docsearchurl':'http://www.google.com/search?q=%filtername%+Avisynth',
                # TEXT OPTIONS
                'calltips': True,
                'frequentcalltips': False,
                'syntaxhighlight': True,
                'usestringeol': True,
                'autocomplete': True,
                'autocompletelength': 1,
                'autocompleteexclusions': set(),
                'autoparentheses': 1,
                'presetactivatekey': 'return',
                'wrap': False,
                'highlightline': True,
                'usetabs': False,
                'tabwidth': 4,
                'numlinechars': 1,
                'foldflag': 1,
                'autocompletesingle': True,
                'autocompletevariables': True,
                'autocompleteicons': True,
                'calltipsoverautocomplete': False,
                # VIDEO OPTIONS
                'dragupdate': True,
                'focusonrefresh': True,
                'previewunsavedchanges': True,
                'hidepreview': False,
                'refreshpreview': True,
                'promptwhenpreview': False,
                'separatevideowindow': False,
                #~ 'showvideopixelinfo': True,
                #~ 'pixelcolorformat': 'hex',
                'videostatusbarinfo': None,
                'cropminx': 16,
                'cropminy': 16,
                #~ 'zoomresizescript': 'BicubicResize(width-width%8, height-height%8, b=1/3, c=1/3)',
                'customjump': 10,
                'customjumpunits': 'sec',
                'enabletabscrolling': True,
                'enableframepertab': True,
                # AUTOSLIDER OPTIONS
                'keepsliderwindowhidden': False,
                'autoslideron': True,
                'autosliderstartfold': 0, #1,
                'autoslidermakeintfloat': True,
                'autoslidermakecolor': True,
                'autoslidermakebool': True,
                'autoslidermakestringlist': True,
                'autoslidermakestringfilename': True,
                'autoslidermakeunknown': True,
                'autosliderexclusions': '',
                # MISC OPTIONS
                'lang': 'eng',
                'startupsession': True,
                'alwaysloadstartupsession': False,
                'promptexitsave': True,
                'savemarkedavs': True,
                'loadstartupbookmarks': True,
                'nrecentfiles': 5,
                'allowresize': True,
                'mintextlines': 2,
                'usetabimages': True,
                'multilinetab': False,
                'fixedwidthtab': False,
                'dllnamewarning': True,
                # TOGGLE OPTIONS
                'alwaysontop': False,
                'singleinstance': False,
                'usemonospacedfont': False,
                'disablepreview': False,
                'paranoiamode': False,
                'autoupdatevideo': False,
            }
            # Import certain options from older version if necessary
            if oldOptions is not None:
                # Update the new options dictionnary with the old options
                updateInfo = [(k,v) for k,v in oldOptions.items() if k in self.options]
                self.options.update(updateInfo)
                #~ for key in self.options.keys():
                    #~ if key in oldOptions:
                        #~ self.options[key] = optionsDict[key]
                # Update the new options sub-dictionnaries with the old options
                for key, d1 in (('templates', templateDict), ('textstyles', textstylesDict)):
                    d2 = oldOptions.get(key)
                    if d2 is not None:
                        d1.update(d2)
                    self.options[key] = d1
                #~ for key, value in templateDict.items():
                    #~ self.options['templates'].setdefault(key, value)
                #~ for key, value in textStyles.items():
                    #~ if not self.optionsTextStyles.has_key(key):
                        #~ self.optionsTextStyles[key] = value
            self.options['version'] = self.version
        # Get the avisynth directory as necessary
        if not os.path.isdir(self.options['avisynthdir']):
            try:
                # Get the avisynth directory from the registry
                key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, 'Software\\AviSynth')
                name, value, typereg = _winreg.EnumValue(key, 0)
                if os.path.isdir(value):
                    self.options['avisynthdir'] = value
                else:
                    raise WindowsError
                key.Close()
            except WindowsError:
                # Get the avisynth directory from the user with a dialog box
                defaultdir = os.environ.get('PROGRAMFILES')
                if defaultdir is None:
                    defaultdir = ''
                dlg = wx.DirDialog(self, 'Select the Avisynth directory', defaultdir)
                ID = dlg.ShowModal()
                if ID==wx.ID_OK:
                    self.options['avisynthdir'] = dlg.GetPath()
                dlg.Destroy()
        self.options['avisynthhelpfile'] = self.options['avisynthhelpfile'].replace('%avisynthdir%', self.options['avisynthdir'])
        # Fix recentfiles as necessary???
        try:
            for i, s in enumerate(self.options['recentfiles']):
                if type(s) != unicode:
                    self.options['recentfiles'][i] = unicode(s, encoding)
        except TypeError:
            pass
                
        # check new key to make options.dat compatible for all 2.x version
        self.options['textstyles'].setdefault('endcomment', 'face:Verdana,size:10,fore:#C0C0C0,back:#FFFFFF')
        self.options['textstyles'].setdefault('blockcomment', 'face:Comic Sans MS,size:9,fore:#007F00,back:#FFFFFF')
        #~ clr = wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE).GetAsString(wx.C2S_HTML_SYNTAX)
        rgb = tuple(map(lambda x: (x+255)/2, wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DFACE).Get()))
        clr = self.options['textstyles'].setdefault('foldmargin', 'back:#%02X%02X%02X' % rgb)
        self.options['textstyles']['foldmargin'] = clr.split(',')[-1]
        self.options['cropminx'] = self.options['cropminy'] = 1
        self.options['loadstartupbookmarks'] = True
        self.options['textstyles'].setdefault('highlightline', 'back:#E8E8FF')
        self.options['textstyles'].setdefault('scrapwindow', 'face:Comic Sans MS,size:10,fore:#0000AA,back:#F5EF90')

    def defineFilterInfo(self):
        self.optionsFilters = self.getFilterInfoFromAvisynth()
        self.installedfilternames = set(self.optionsFilters) #set([key.lower() for key in self.optionsFilters.keys()])
        if __debug__:
            self.ExportFilterData(self.optionsFilters, 'tempfilterout.txt', True)
        self.avskeywords = [
            'return', 'global', 'function', 'last',
            'true', 'false', 'try', 'catch',
        ]
        self.avsdatatypes = [
            'clip', 'int', 'float', 'string', 'bool', 'var',
        ]
        self.avsoperators = [
            '-', '*', ',', '.', '/', ':', '?', '\\', '+', '<', '>', '=',
            '(', ')', '[', ']', '{', '}', '!', '%', '&', '|',
        ]
        self.avsmiscwords = ['__end__']
        if os.path.exists(self.filterdbfilename):
            f = open(self.filterdbfilename, mode='r')
            text = '\n'.join([line.strip() for line in f.readlines()])
            f.close()
            for section in text.split('\n['):
                title, data = section.split(']\n',1)
                title = title.strip('[]').lower()
                if title == 'keywords':
                    self.avskeywords = data.split()
                elif title == 'datatypes':
                    self.avsdatatypes = data.split()
                elif title == 'operators':
                    self.avsoperators = data.split()
                elif title == 'clipproperties':
                    for item in data.split('\n'):
                        if not item.strip():
                            continue
                        splitstring = item.split('(', 1)
                        if len(splitstring) == 2:
                            filtername = splitstring[0].strip()
                            filterargs = '('+splitstring[1].strip(' ')
                        else:
                            filtername = item
                            filterargs = ''
                        self.optionsFilters[filtername.lower()] = (filtername, filterargs, 1)
                elif title == 'scriptfunctions':
                    for item in data.split('\n'):
                        splitstring = item.split('(', 1)
                        if len(splitstring) == 2:
                            filtername = splitstring[0].strip()
                            filterargs = '('+splitstring[1].strip(' ')
                            self.optionsFilters[filtername.lower()] = (filtername, filterargs, 4)
                elif title == 'corefilters':
                    for s in data.split('\n\n'):
                        splitstring = s.split('(', 1)
                        if len(splitstring) == 2:
                            filtername = splitstring[0].strip()
                            filterargs = '('+splitstring[1].strip(' ')
                            self.optionsFilters[filtername.lower()] = (filtername, filterargs, 0)
                elif title == 'plugins':
                    for s in data.split('\n\n'):
                        splitstring = s.split('(', 1)
                        if len(splitstring) == 2:
                            filtername = splitstring[0].strip()
                            filterargs = '('+splitstring[1].strip(' ')
                            #~ if filtername.lower() in self.optionsFilters:
                                #~ self.optionsFilters[filtername.lower()] = (filtername, filterargs, 2)
                            key = filtername.lower()
                            self.optionsFilters[key] = (filtername, filterargs, 2)
                            #~ splitname = filtername.split('_', 1)
                            #~ if len(splitname) == 2:
                                #~ filtername = splitname[1]
                                #~ self.optionsFilters[filtername.lower()] = (filtername, filterargs, 2)
                            if key in self.options['filterdb']:
                                del self.options['filterdb'][key]
                elif title == 'userfunctions':
                    for s in data.split('\n\n'):
                        splitstring = s.split('(', 1)
                        if len(splitstring) == 2:
                            filtername = splitstring[0].strip()
                            filterargs = '('+splitstring[1].strip(' ')
                            self.optionsFilters[filtername.lower()] = (filtername, filterargs, 3)
        # Clean up override dict
        deleteKeys = []
        #~ for key, value in self.options['filteroverrides'].items():
            #~ if key.count('_') == 0:
                #~ tempList = [(k.split('_', 1), v[0]) for k, v in self.optionsFilters.items()]
                #~ for longKey, v in tempList[:]:
                    #~ if len(longKey) != 2 or longKey[-1] != key:
                        #~ tempList.remove((longKey, v))
                #~ if len(tempList) == 1: 
                    #~ longKey, longName = tempList[0]
                    #~ longKey = '_'.join(longKey)
                    #~ shortname, filterargs, type = value
                    #~ self.options['filteroverrides'][longKey] = (longName, filterargs, type)
                    #~ deleteKeys.append(key)
        for key, value in self.options['filteroverrides'].items():
            if key in self.optionsFilters and self.optionsFilters[key] == value:
                deleteKeys.append(key) 
        for key in deleteKeys:
            del self.options['filteroverrides'][key]        
        for key, value in self.options['filterdb'].items():
            if key not in self.optionsFilters:
                if key not in self.options['filteroverrides'] and key not in self.options['filterpresets']:
                    del self.options['filterdb'][key]
                    if key in self.options['filterremoved']:
                        self.options['filterremoved'].remove(key)
                    if value[0] in self.options['autocompleteexclusions']:
                        self.options['autocompleteexclusions'].remove(value[0])                        
                else:
                    self.options['filteroverrides'].setdefault(key, value)
        # Define data structures that are used by each script
        self.defineScriptFilterInfo()

    def ExportFilterData(self, filterDict, filename, onlylongnames=False):
        order = [1, 4, 0, 2, 3]
        keysdec = [(order.index(v[2]), k) for k,v in filterDict.items()]
        keysdec.sort()
        lines = []
        typeDict = {
            0: '[COREFILTERS]',
            1: '[CLIPPROPERTIES]',
            2: '[PLUGINS]',
            3: '[USERFUNCTIONS]',
            4: '[SCRIPTFUNCTIONS]',
        }
        currentType = None
        for keysortindex, key in keysdec:
            keytype = order[keysortindex]
            if keytype != currentType:
                extra = ''
                if len(lines) > 0:
                    if not lines[-1].endswith('\n\n'):
                        extra = '\n'
                lines.append(extra+typeDict[keytype]+'\n')
                currentType = keytype
            propername, args, ftype = filterDict[key]
            #~ if args.count('\n') != 0:
                #~ continue
            if onlylongnames and ftype == 2 and key.count('_') == 0:
                continue
            if ftype in (1, 4):
                line = propername+args+'\n'
            else:
                if args.count('\n') == 0:
                    line = '%s(\n%s\n)\n\n' % (propername, ',\n'.join(args.strip('()').split(', ')))
                    line = line.replace('[,\n...]', '[, ...]')
                else:
                    line = propername+args+'\n\n'
            lines.append(line)
        f = open(filename, 'w')
        f.writelines(lines)
        f.close()

    def defineScriptFilterInfo(self):
        # Create the basic filter dictionnary - {lowername: (args, style_constant)}
        styleList = [  # order is important here!
            AvsStyledTextCtrl.STC_AVS_COREFILTER,
            AvsStyledTextCtrl.STC_AVS_CLIPPROPERTY,
            AvsStyledTextCtrl.STC_AVS_PLUGIN,
            AvsStyledTextCtrl.STC_AVS_USERFUNCTION,
            AvsStyledTextCtrl.STC_AVS_SCRIPTFUNCTION,
        ]
        self.avsfilterdict = dict(
            [
            (lowername, (args, styleList[ftype], name))
            for lowername,(name,args,ftype) in self.optionsFilters.items()
            if lowername not in self.options['filterremoved']
            ]
        )
        overridedict = dict(
            [
            (lowername, (args, styleList[ftype], name))
            for lowername,(name,args,ftype) in self.options['filteroverrides'].items()
            if lowername not in self.options['filterremoved']
            ]
        )
        self.avsfilterdict.update(overridedict)
        # Add short plugin names to script database
        for lowername,(args,styletype,name) in self.avsfilterdict.items():
            if styletype == styleList[2]:
                shortname = None
                for dllname in sorted(self.dllnameunderscored, reverse=True):
                    if name.lower().startswith(dllname):
                        shortname = name[len(dllname)+1:]
                        if shortname.lower() not in self.avsfilterdict or self.avsfilterdict[shortname.lower()][1] != styleList[3]:
                            self.avsfilterdict[shortname.lower()] = (args, styletype, shortname)
                        break
                if not shortname:
                    splitname = name.split('_', 1)
                    if len(splitname) == 2:
                        shortname = splitname[1]
                        if shortname.lower() not in self.avsfilterdict or self.avsfilterdict[shortname.lower()][1] != styleList[3]:
                            self.avsfilterdict[shortname.lower()] = (args, styletype, shortname)
        #~ self.optionsFilters.update(self.options['filteroverrides'])
        # Create a list for each letter (for autocompletion)
        filternames = [
            lowername
            for lowername,(args,style,name) in self.avsfilterdict.items()
            if self.options['autcompletetypeflags'][styleList.index(style)]
        ]
        #~ filternames = self.avsfilterdict.keys()
        filternames.sort()
        self.avsazdict = {}
        for lowername in filternames:
            letter = lowername[0]
            letterlist = self.avsazdict.setdefault(letter, [])
            hasSymbol = False
            if not lowername[0].isalpha() and lowername[0] != '_':
                hasSymbol = True
            else:
                for char in lowername:
                    if not char.isalnum() and char != '_':
                        hasSymbol = True
                        break
            if not hasSymbol:
                letterlist.append(self.avsfilterdict[lowername][2])
        self.avssingleletters = [
            s for s in (self.avsfilterdict.keys()+self.avskeywords+self.avsmiscwords)
            if (len(s) == 1 and not s.isalnum() and s != '_')
        ]

    def getFilterInfoFromAvisynth(self):
        self.dllnameunderscored = set()
        try:
            avisynth
        except NameError:
            return {}
        try:
            env = avisynth.avs_create_script_environment(3)
        except WindowsError:
            return {}
        intfunc = avisynth.avs_get_var(env,"$InternalFunctions$")
        intfuncList = [(name, 0) for name in intfunc.d.s.split()]
        intfunc.Release()
        extfunc = avisynth.avs_get_var(env,"$PluginFunctions$")
        if extfunc.d.s is not None:
            s = extfunc.d.s + ' '
            extfunc.Release()
            extfuncList = []
            dllnameList = []
            start = 0
            end = len(s)            
            while start < end:
                pos = s.find(' ', start)
                if pos == -1 or pos == end-1:
                    print>>sys.stderr, 'Error parsing plugin string at position %d:\n%s' % (start, s)
                    break
                shortname = '_' + s[start:pos+1]
                start = pos + 1
                pos = s.find(shortname, start)
                if pos == -1:
                    print>>sys.stderr, 'Error parsing plugin string at position %d:\n%s' % (start, s)
                    break
                dllname = s[start:pos]
                if dllname in dllnameList:
                    pass
                elif not dllname[0].isalpha() and dllname[0] != '_':
                    dllnameList.append(dllname)
                else:
                    for char in dllname:
                        if not char.isalnum() and char != '_':
                            dllnameList.append(dllname)
                            break
                pos += len(shortname)
                extfuncList.append((s[start:pos-1], 2))
                if dllname.count('_'):
                    self.dllnameunderscored.add(dllname.lower())
                start = pos
            funclist = intfuncList + extfuncList
            if dllnameList and self.options['dllnamewarning']:
                self.IdleCall.append((self.ShowWarningOnBadNaming, (dllnameList, ), {}))
        else:
            funclist = intfuncList
        typeDict = {
            'c': 'clip',
            'i': 'int',
            'f': 'float',
            'b': 'bool',
            's': 'string',
            '.': 'var',
            #~ '*': '[...]',
        }
        functionDict = {}
        for name, functionType in funclist:
            if name.strip() == '':
                continue
            t = avisynth.avs_get_var(env,"$Plugin!"+name+"!Param$")
            if t.d.c is not None:
                argList = []
                namedarg = False
                namedargname = []
                for i, c in enumerate(t.d.s):
                    if c == '[':
                        namedarg = True
                    elif c == ']':
                        namedarg = False
                    elif namedarg:
                        namedargname.append(c)
                    else:
                        namedargindex = len(argList)
                        if c in ('+', '*'):
                            try:
                                typeDict[t.d.s[i-1]] # Helps ensure previous arg is valid
                                argList[-1] += ' [, ...]'
                            except (IndexError, KeyError):
                                print>>sys.stderr, (
                                    'Error parsing %s plugin parameters: '
                                    '+ without preceeding argument') % name
                        else:
                            try:
                                typeValue = typeDict[c]
                            except KeyError:
                                print>>sys.stderr, (
                                    'Error parsing %s plugin parameters: '
                                    'unknown character %s') % (name, c)
                                typeValue = '?'
                            argList.append(typeValue)
                        if namedargname:
                            try:
                                argList[namedargindex] += ' '+''.join(namedargname)
                            except IndexError:
                                print>>sys.stderr, (
                                    'Error parsing %s plugin parameters: '
                                    '[name] without following argument') % name
                                argList.append(''.join(namedargname))
                            namedargname = []
                argstring = '(%s)' % (', '.join(argList))
            t.Release()
            if functionType == 0:
                if name.islower():
                    if argstring == '(clip)':
                        functionType = 1
                        argstring = ''
                    else:
                        functionType = 4
                elif argstring == '(clip)':
                    boolIsXXX = len(name) > 2 and name.startswith('Is') and name[2].isupper()
                    boolHasXXX = len(name) > 3 and name.startswith('Has') and name[3].isupper()
                    boolGetXXX = len(name) > 3 and name.startswith('Get') and name[3].isupper()
                    if boolIsXXX or boolHasXXX or boolGetXXX:
                        functionType = 1
                        argstring = '()'
            key = name.lower()
            functionDict[key] = (name, argstring, functionType)
            if functionType == 2:
                self.options['filterdb'][key] = (name, argstring, functionType)
        env.Release()
        return functionDict

    def wrapFilterCalltip(self, txt, maxchars=80):
        if txt.count('\n') > 0:
            return txt
        args = txt.split(',')
        argList = []
        count = 0
        lastArg = len(args) - 1
        for i, arg in enumerate(args):
            arg = arg.strip()
            if i != lastArg: #not arg.endswith(')'):
                arg += ', '
            count += len(arg)
            if count <= maxchars:
                argList.append(arg)
            else:
                argList.append('\n'+arg)
                count = len(arg)
        return ''.join(argList)

    def getOptionsDlgInfo(self):
        return (
            (_('Paths'),
                ((_('AvsP help directory:'), wxp.OPT_ELEM_DIR, 'helpdir', _('Location of the AvsP help directory'), dict(buttonText='...', buttonWidth=30) ), ),
                ((_('Avisynth directory:'), wxp.OPT_ELEM_DIR, 'avisynthdir', _('Location of the avisynth installation directory'), dict(buttonText='...', buttonWidth=30) ), ),
                ((_('Avisynth help file/url:'), wxp.OPT_ELEM_FILE_URL, 'avisynthhelpfile', _('Location of the avisynth help file or url'), dict(buttonText='...', buttonWidth=30) ), ),
                ((_('External player:'), wxp.OPT_ELEM_FILE, 'externalplayer', _('Location of external program for script playback'), dict(fileMask='Executable files (*.exe)|*.exe', buttonText='...', buttonWidth=30) ), ),
                ((_('External player extra args:'), wxp.OPT_ELEM_STRING, 'externalplayerargs', _('Additional arguments when running the external player'), dict() ), ),
                ((_('Documentation search paths:'), wxp.OPT_ELEM_STRING, 'docsearchpaths', _('Specify which directories to search for docs when you click on a filter calltip'), dict() ), ),
                ((_('Documentation search url:'), wxp.OPT_ELEM_STRING, 'docsearchurl', _("The web address to search if docs aren't found (the filter's name replaces %filtername%)"), dict() ), ),
            ),
            (_('Text'),
                ((_('Show filter calltips'), wxp.OPT_ELEM_CHECK, 'calltips', _('Turn on/off automatic tips when typing filter names'), dict() ), ),
                ((_('Frequent calltips'), wxp.OPT_ELEM_CHECK, 'frequentcalltips', _("Always show calltips any time the cursor is within the filter's arguments"), dict(ident=20) ), ),
                ((_('Syntax highlighting'), wxp.OPT_ELEM_CHECK, 'syntaxhighlight', _('Turn on/off avisynth-specific text colors and fonts'), dict() ), ),
                #~((_('Syntax highlight incomplete strings'), wxp.OPT_ELEM_CHECK, 'usestringeol', _('Syntax highlight strings which are not completed in a single line differently'), dict() ), ),
                #~((_('Highlight current line'), wxp.OPT_ELEM_CHECK, 'highlightline', _('Highlight the line that the caret is currently in'), dict() ), ),
                #~(('       '+_('Highlight line color'), wxp.OPT_ELEM_COLOR, 'highlightlinecolor', _('Change the the highlight line color'), dict() ), ),
                ((_('Show autocomplete on capital letters'), wxp.OPT_ELEM_CHECK, 'autocomplete', _('Turn on/off automatic autocomplete list when typing words starting with capital letters'), dict() ), ),
                ((_('       '+'Amount of letters typed'), wxp.OPT_ELEM_SPIN, 'autocompletelength', _('Show autocomplete list when typing a certain amount of letters'), dict() ), ),
                #~((_('Use monospaced font'), wxp.OPT_ELEM_CHECK, 'usemonospacedfont', _('Override all fonts to use a specified monospace font'), dict() ), ),
                ((_('Wrap text'), wxp.OPT_ELEM_CHECK, 'wrap', _("Don't allow lines wider than the window"), dict() ), ),
                ((_('Draw lines at fold points'), wxp.OPT_ELEM_CHECK, 'foldflag', _('For code folding, draw a line underneath if the fold point is not expanded'), dict() ), ),
                ((_('Use tabs instead of spaces'), wxp.OPT_ELEM_CHECK, 'usetabs', _('Check to insert actual tabs instead of spaces when using the Tab key'), dict() ), ),
                ((_('Tab width'), wxp.OPT_ELEM_SPIN, 'tabwidth', _('Set the size of the tabs in spaces'), dict() ), ),
                ((_('Line margin width'), wxp.OPT_ELEM_SPIN, 'numlinechars', _('Initial space to reserve for the line margin in terms of number of digits'), dict() ), ),
            ),
            (_('Autocomplete'),
                ((_('Show autocomplete with variables'), wxp.OPT_ELEM_CHECK, 'autocompletevariables', _('Add user defined variables into autocomplete list'), dict() ), ),
                ((_('Show autocomplete on single matched lowercase variable'), wxp.OPT_ELEM_CHECK, 'autocompletesingle', _('When typing a lowercase variable name, show autocomplete if there is only one item matched in keyword list'), dict(ident=20) ), ),
                ((_('Show autocomplete with icons'), wxp.OPT_ELEM_CHECK, 'autocompleteicons', _("Add icons into autocomplete list. Using different type to indicate how well a filter's presets is defined"), dict() ), ),
                ((_("Don't show autocomplete when calltip is active"), wxp.OPT_ELEM_CHECK, 'calltipsoverautocomplete', _('When calltip is active, autocomplete will not be activate automatically. You can still show autocomplete manually'), dict() ), ),
                ((_('Customize autocomplete keyword list...'), wxp.OPT_ELEM_BUTTON, 'autocompleteexclusions', _('Customize the keyword list shown in the autocomplete choice box'), dict(handler=self.OnCustomizeAutoCompList) ), ),
                ((_('Autoparentheses level'), wxp.OPT_ELEM_RADIO, 'autoparentheses', _('Determines parentheses to insert upon autocompletion'), dict(choices=[(_('None " "'), 0),(_('Open "("'), 1),(_('Close "()"'), 2)])), ),
                ((_('Preset activation key'), wxp.OPT_ELEM_RADIO, 'presetactivatekey', _('Determines which key activates the filter preset when the autocomplete box is visible'), dict(choices=[(_('Tab'), 'tab'),(_('Return'), 'return'),(_('None'), None)]) ), ),
            ),
            (_('Video'),
                ((_('Constantly update video while dragging'), wxp.OPT_ELEM_CHECK, 'dragupdate', _('Update the video constantly when dragging the frame slider'), dict() ), ),
                ((_('Enable line-by-line update'), wxp.OPT_ELEM_CHECK, 'autoupdatevideo', _('Enable the line-by-line video update mode (update every time the cursor changes line position)'), dict() ), ),
                ((_('Focus the video preview upon refresh'), wxp.OPT_ELEM_CHECK, 'focusonrefresh', _('Switch focus to the video preview window when using the refresh command'), dict() ), ),
                ((_('Refresh preview automatically'), wxp.OPT_ELEM_CHECK, 'refreshpreview', _('Refresh preview when switch focus on video window or change a value in slider window'), dict() ), ),
                ((_('Shared timeline'), wxp.OPT_ELEM_CHECK, 'enableframepertab', _('Seeking to a certain frame will seek to that frame on all tabs'), dict() ), ),
                ((_('Allow AvsPmod to resize the window'), wxp.OPT_ELEM_CHECK, 'allowresize', _('Allow AvsPmod to resize and/or move the program window when updating the video preview'), dict() ), ),
                ((_('Separate video preview window')+' *', wxp.OPT_ELEM_CHECK, 'separatevideowindow', _('Use a separate window for the video preview'), dict() ), ),
                ((_('Min text lines on video preview')+' *', wxp.OPT_ELEM_SPIN, 'mintextlines', _('Minimum number of lines to show when displaying the video preview'), dict() ), ),
                ((_('Customize video status bar...'), wxp.OPT_ELEM_BUTTON, 'videostatusbarinfo', _('Customize the video information shown in the program status bar'), dict(handler=self.OnConfigureVideoStatusBarMessage) ), ),
            ),
            (_('User Sliders'),
                ((_('Hide slider window by default'), wxp.OPT_ELEM_CHECK, 'keepsliderwindowhidden', _('Keep the slider window hidden by default when previewing a video'), dict() ), ),
                ((_('Create user sliders automatically'), wxp.OPT_ELEM_CHECK, 'autoslideron', _('Create user sliders automatically using the filter database'), dict() ), ),
                ((_('type int/float (numerical slider)'), wxp.OPT_ELEM_CHECK, 'autoslidermakeintfloat', _('Create user sliders for int and float arguments'), dict(ident=20) ), ),
                ((_('type int (hex color)'), wxp.OPT_ELEM_CHECK, 'autoslidermakecolor', _('Create color pickers for hex color arguments'), dict(ident=20) ), ),
                ((_('type bool'), wxp.OPT_ELEM_CHECK, 'autoslidermakebool', _('Create radio boxes for bool arguments'), dict(ident=20) ), ),
                ((_('type string (list)'), wxp.OPT_ELEM_CHECK, 'autoslidermakestringlist', _('Create listboxes for string list arguments'), dict(ident=20) ), ),
                ((_('type string (filename)'), wxp.OPT_ELEM_CHECK, 'autoslidermakestringfilename', _('Create filename pickers for string filename arguments'), dict(ident=20) ), ),
                ((_('undocumented'), wxp.OPT_ELEM_CHECK, 'autoslidermakeunknown', _('Create placeholders for arguments which have no database information'), dict(ident=20) ), ),
                ((_('Fold startup setting'), wxp.OPT_ELEM_RADIO, 'autosliderstartfold', _('Determines which filters will initially have hidden arguments in the slider window'), dict(choices=[(_('Fold all'), 0),(_('Fold none'), 1),(_('Fold non-numbers'), 2)]) ), ),
                ((_('Filter exclusion list:'), wxp.OPT_ELEM_STRING, 'autosliderexclusions', _('Specify filters never to build automatic sliders for'), dict() ), ),
            ),
            (_('Save/Load'),
                ((_('Save session for next launch'), wxp.OPT_ELEM_CHECK, 'startupsession', _('Automatically save the session on shutdown and load on next startup'), dict() ), ),
                ((_('Always load startup session'), wxp.OPT_ELEM_CHECK, 'alwaysloadstartupsession', _('Always load the auto-saved session before opening any other file on startup'), dict() ), ),
                ((_("Don't preview when loading a session"), wxp.OPT_ELEM_CHECK, 'hidepreview', _('Always hide the video preview window when loading a session'), dict() ), ),
                ((_('Backup session when previewing'), wxp.OPT_ELEM_CHECK, 'paranoiamode', _('If checked, the current session is backed up prior to previewing any new script'), dict() ), ),
                ((_('Prompt to save when previewing'), wxp.OPT_ELEM_CHECK, 'promptwhenpreview', _('Prompt to save a script before previewing (inactive if previewing with unsaved changes)'), dict() ), ),
                ((_('Preview scripts with unsaved changes'), wxp.OPT_ELEM_CHECK, 'previewunsavedchanges', _('Create a temporary preview script with unsaved changes when previewing the video'), dict() ), ),
                ((_('Prompt to save scripts on program exit'), wxp.OPT_ELEM_CHECK, 'promptexitsave', _('Prompt to save each script with unsaved changes when exiting the program'), dict() ), ),
                ((_('Save *.avs scripts with AvsPmod markings'), wxp.OPT_ELEM_CHECK, 'savemarkedavs', _('Save AvsPmod-specific markings (user sliders, toggle tags, etc) as a commented section in the *.avs file'), dict() ), ),
            ),
            (_('Misc'),
                ((_('Language *'), wxp.OPT_ELEM_LIST, 'lang', _('Choose the language used for the interface'), dict(choices=self.getTranslations()) ), ),
                #~((_('Load bookmarks on startup'), wxp.OPT_ELEM_CHECK, 'loadstartupbookmarks', _('Load video bookmarks from the previous session on program startup'), dict() ), ),
                #~ ((_('Show full pathname in program title'), wxp.OPT_ELEM_CHECK, 'showfullname', _('Show the full pathname of the current script in the program title'), dict() ), ),
                #~ ((_('Use custom AviSynth lexer'), wxp.OPT_ELEM_CHECK, 'usecustomlexer', _('Use the custom AviSynth syntax highlighting lexer (may be slower)'), dict() ), ),
                ((_('Use keyboard images in tabs'), wxp.OPT_ELEM_CHECK, 'usetabimages', _('Show keyboard images in the script tabs when video has focus'), dict() ), ),
                ((_('Show tabs in multiline style'), wxp.OPT_ELEM_CHECK, 'multilinetab', _('There can be several rows of tabs'), dict() ), ),
                ((_('Show tabs in fixed width'), wxp.OPT_ELEM_CHECK, 'fixedwidthtab', _('All tabs will have same width'), dict() ), ),
                ((_('Enable scroll wheel through similar tabs'), wxp.OPT_ELEM_CHECK, 'enabletabscrolling', _('Mouse scroll wheel cycles through tabs with similar videos'), dict() ), ),
                ((_('Only allow a single instance of AvsPmod')+' *', wxp.OPT_ELEM_CHECK, 'singleinstance', _('Only allow a single instance of AvsPmod'), dict() ), ),
                ((_('Show warning for bad plugin naming at startup'), wxp.OPT_ELEM_CHECK, 'dllnamewarning', _('Show warning at startup if there are dlls with bad naming in default plugin folder'), dict() ), ),
                ((_('Max number of recent filenames'), wxp.OPT_ELEM_SPIN, 'nrecentfiles', _('This number determines how many filenames to store in the recent files menu'), dict() ), ),
                ((_('Custom jump size:'), wxp.OPT_ELEM_SPIN, 'customjump', _('Jump size used in video menu'), dict() ), ),
                ((_('Custom jump size units'), wxp.OPT_ELEM_RADIO, 'customjumpunits', _('Units of custom jump size'), dict(choices=[(_('frames'), 'frames'),(_('seconds'), 'sec'),(_('minutes'), 'min'),(_('hours'), 'hr')]) ), ),
            ),
        )

    def UpdateTranslationFile(self):
        newmark = ' # New in v%s' % version
        # Get the text from the translation file
        filename = os.path.join(self.programdir, self.translations_dir, 'translation_%s.py' % self.options['lang'])
        if os.path.isfile(filename):
            f = open(filename, 'r')
            txt = f.read()
            f.close()
        else:
            txt = ''
        # Setup the new text...
        oldMessageDict = {}
        oldMessageDict2 = {}
        allMessagesMatched = True
        if not txt.strip():
            newmark = ''
            newlines = (
            '# -*- coding: utf-8 -*-\n'
            '\n'
            '# This file is used to translate the messages used in the AvsPmod interface.\n'
            '# To use it, make sure it is named "translation_lng.py" where "lng" is the \n'
            '# three-letter code corresponding to the language that is translated to \n'
            '# (see <http://www.loc.gov/standards/iso639-2/php/code_list.php>), \n'
            '# and is placed in the "%s" subdirectory.\n' % self.translations_dir +
            '# \n'
            '# Simply add translated messages next to each message (any untranslated \n'
            '# messages will be shown in English).  You can type unicode text directly \n'
            '# into this document - if you do, make sure to save it in the appropriate \n'
            '# format.  If required, you can change the coding on the first line of this \n'
            '# document to a coding appropriate for your translated language. DO NOT \n'
            '# translate any words inside formatted strings (ie, any portions of the \n'
            '# text which look like %(...)s, %(...)i, etc.)\n'
            ).split('\n')
        else:
            newlines = []
            boolStartLines = True
            re_mark = re.compile(r'(.*(?<![\'"])[\'"],)\s*#')
            for line in txt.split('\n'):
                # Copy the start lines
                if line.strip() and not line.lstrip('\xef\xbb\xbf').strip().startswith('#'):
                    boolStartLines = False
                if boolStartLines:
                    newlines.append(line)
                # Get the key
                splitline = line.split(' : ', 1)
                if len(splitline) == 2:
                    key = splitline[0].strip()
                    match = re_mark.match(line)
                    oldMessageDict[key] = match.group(1) if match else line
                    # Heuristically add extra keys for similar enough messages
                    if splitline[1].strip().startswith('u"'):
                        rawkey = key.strip('"')
                        splitvalue = splitline[1].strip().split('"')
                        if rawkey.endswith(':'):
                            key2 = '"%s"' % rawkey.rstrip(':')
                            splitvalue[1] = splitvalue[1].rstrip(':')
                            line2 = '    ' + key2 + ' : ' + '"'.join(splitvalue)
                            oldMessageDict2[key2] = line2
                        elif rawkey.endswith(' *'):
                            key2 = '"%s"' % rawkey.rstrip(' *')
                            splitvalue[1] = splitvalue[1].rstrip(' *')
                            line2 = '    ' + key2 + ' : ' + '"'.join(splitvalue)
                            oldMessageDict2[key2] = line2
                        elif rawkey and (rawkey[0].isspace() or rawkey[-1].isspace()):
                            key2 = '"%s"' % rawkey.strip()
                            splitvalue[1] = splitvalue[1].strip()
                            line2 = '    ' + key2 + ' : ' + '"'.join(splitvalue)
                            oldMessageDict2[key2] = line2
        # Get the new translation strings and complete the new text
        curlines = new_translation_string.split('\n')
        for line in curlines:
            splitline = line.split(' : ')
            if line.startswith('    ') and len(splitline) > 1:
                key = splitline[0].strip()
                if key in oldMessageDict:
                    newlines.append(oldMessageDict[key])
                elif key in oldMessageDict2:
                    newlines.append(oldMessageDict2[key])
                else:
                    newlines.append(line+newmark)
                    allMessagesMatched = False
            else:
                newlines.append(line)
        # Overwrite the text file with the new data
        f = open(filename, 'w')
        f.write('\n'.join(newlines))
        f.close()
        return not allMessagesMatched
    
    def getTranslations(self):
        '''Return the list of 'translation_lng.py' files within the translations subfolder'''
        translation_list = {'eng'}
        re_lng = re.compile(r'translation_(\w{3})\.py[co]?', re.I)
        if os.path.isdir(self.translations_dir):
            for file in os.listdir(self.translations_dir): 
                match = re_lng.match(file)
                if match:
                    translation_list.add(match.group(1))
        return sorted(translation_list)
    
    def createWindowElements(self):
        # Create the program's status bar
        statusBar = self.CreateStatusBar(2)
        statusBar.SetStatusWidths([-1, 0])

        # Create the main subwindows
        if wx.VERSION < (2, 9):
            self.programSplitter = wx.SplitterWindow(self, wx.ID_ANY, style=wx.SP_NOBORDER)
        else:
            self.programSplitter = self
        self.mainSplitter = wx.SplitterWindow(self.programSplitter, wx.ID_ANY, style=wx.SP_3DSASH|wx.SP_NOBORDER|wx.SP_LIVE_UPDATE)
        if not self.separatevideowindow:
            parent = self.mainSplitter
        else:
            #~ self.videoDialog = wx.Dialog(self, wx.ID_ANY, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
            self.videoDialog = wx.Frame(self, wx.ID_ANY,style=wx.DEFAULT_FRAME_STYLE|wx.WANTS_CHARS)#, style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
            dimensions = self.options.get('dimensions2')
            if dimensions is not None and dimensions[0] > 0 and dimensions[1] > 0:
                self.videoDialog.SetDimensions(*dimensions)
                # Move the window if it's offscreen
                size = self.videoDialog.GetSize()
                pos = self.videoDialog.GetPosition()
                wC, hC = wx.ScreenDC().GetSize()
                #~ if (pos[0]+size[0]>wC) or (pos[1]+size[1]>hC):
                if (pos[0]+50>wC) or (pos[1]+50>hC):
                    self.videoDialog.Center()
            self.videoDialog.SetIcon(AvsP_icon.getIcon())
            self.videoDialog.Bind(wx.EVT_CLOSE, self.OnMenuVideoHide)
            def OnVideoDialogActivate(event):
                if event.GetActive():
                    self.ShowVideoFrame()
                event.Skip()
            self.videoDialog.Bind(wx.EVT_ACTIVATE, OnVideoDialogActivate)
            self.videoDialog.oldSize = None
            def OnVideoDialogResizeEnd(event):
                if self.zoomwindow:
                    newSize = event.GetSize()
                    oldSize = self.videoDialog.oldSize
                    if oldSize is not None and newSize == oldSize:
                        #~ self.ShowVideoFrame(forceRefresh=True)
                        self.ShowVideoFrame()
                        self.videoDialog.oldSize = None
                    else:
                        self.videoDialog.oldSize = newSize
                event.Skip()
            self.videoDialog.Bind(wx.EVT_SIZING, OnVideoDialogResizeEnd)
            #~ def OnVideoDialogKeyDown(event):
                #~ keycode = event.GetKeyCode()
                #~ if keycode == wx.WXK_DELETE:
            #~ self.videoDialog.Bind(wx.EVT_KEY_DOWN, OnVideoDialogKeyDown)
            parent = self.videoDialog
        self.videoPane = wx.Panel(parent, wx.ID_ANY)
        self.videoSplitter = wx.SplitterWindow(self.videoPane, wx.ID_ANY, style=wx.SP_3DSASH|wx.SP_NOBORDER|wx.SP_LIVE_UPDATE)

        w = 10
        h = 50
        bmpMask = wx.EmptyBitmap(w, h)
        mdc = wx.MemoryDC()
        mdc.SelectObject(bmpMask)
        mdc.DrawPolygon([(8,0), (2,6), (8,12)])
        mdc.DrawPolygon([(8,18), (2,24), (8,30)])
        mdc.DrawPolygon([(8,36), (2,42), (8,48)])
        mdc = None
        bmpShow = wx.EmptyBitmap(w, h)
        #~ mdc = wx.MemoryDC()
        #~ mdc.SelectObject(bmpShow)
        #~ mdc.SetBackground(wx.Brush(wx.Colour(90, 90, 90)))
        #~ mdc.Clear()
        #~ mdc = None
        bmpShow.SetMask(wx.Mask(bmpMask))
        bmpHide = bmpShow.ConvertToImage().Mirror().ConvertToBitmap()
        self.toggleSliderWindowButton = wxButtons.GenBitmapButton(self.videoPane, wx.ID_ANY, bmpHide, size=(w,h), style=wx.NO_BORDER)
        self.toggleSliderWindowButton.bmpShow = bmpShow
        self.toggleSliderWindowButton.bmpHide = bmpHide
        def OnTSWButtonSize(event):
            dc = wx.WindowDC(self.toggleSliderWindowButton)
            dc.Clear()
            wButton, hButton = self.toggleSliderWindowButton.GetClientSizeTuple()
            self.toggleSliderWindowButton.DrawLabel(dc, wButton, hButton)
            event.Skip()
        self.toggleSliderWindowButton.Bind(wx.EVT_SIZE, OnTSWButtonSize)
        def OnToggleSliderWindowButton(event):
            self.ToggleSliderWindow(vidrefresh=True)
            script = self.currentScript
            script.userHidSliders = not script.sliderWindowShown
            self.videoWindow.SetFocus()
        self.videoPane.Bind(wx.EVT_BUTTON, OnToggleSliderWindowButton, self.toggleSliderWindowButton)
        #~ forwardButton.SetBackgroundColour(wx.BLACK)

        self.videoPaneSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.videoPaneSizer.Add(self.videoSplitter, 1, wx.EXPAND|wx.ALL, 0)
        self.videoPaneSizer.Add(self.toggleSliderWindowButton, 0, wx.EXPAND|wx.ALL, 0)
        self.videoPane.SetSizer(self.videoPaneSizer)
        #~ self.videoPaneSizer.Layout()


        def OnVideoSplitterPosChanged(event):
            if self.zoomwindowfit:
                self.ShowVideoFrame(focus=False)
                #~ self.ShowVideoFrame(forceRefresh=True, focus=False)
                #~ self.IdleCall = (self.ShowVideoFrame, tuple(), {'forceRefresh': True, 'focus': False})
                #~ wx.FutureCall(100, self.ShowVideoFrame, forceRefresh=True, focus=False)
            event.Skip()
        #~ self.videoSplitter.Bind(wx.EVT_LEFT_UP, OnVideoSplitterPosChanged)


        self.mainSplitter.SetSashSize(4)
        self.videoSplitter.SetSashSize(4)
        
        self.programSplitterSize = None
        
        self.mainSplitter.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClickWindow)

        self.clicked_on_divider = False
        def OnMainSplitterLeftDown(event):
            x, y = event.GetPosition()
            if y > self.mainSplitter.GetMinimumPaneSize():
                self.clicked_on_divider = True
            else:
                self.clicked_on_divider = False
            if self.FindFocus() == self.titleEntry:
                self.scriptNotebook.SetFocus()
            event.Skip()
        self.mainSplitter.Bind(wx.EVT_LEFT_DOWN, OnMainSplitterLeftDown)

        def OnMainSplitterPosChanged(event):
            #~ self.lastSplitVideoPos = event.GetSashPosition()
            if self.clicked_on_divider:
                self.currentScript.lastSplitVideoPos = self.mainSplitter.GetSashPosition() - self.mainSplitter.GetClientSize()[1]
                self.clicked_on_divider = False
                if self.zoomwindow:
                    #~ for index in xrange(self.scriptNotebook.GetPageCount()):
                        #~ script = self.scriptNotebook.GetPage(index)
                        #~ self.UpdateScriptAVI(script, forceRefresh=True)
                    #~ self.ShowVideoFrame(forceRefresh=True, focus=False)
                    self.ShowVideoFrame(focus=False)
            event.Skip()
        self.mainSplitter.Bind(wx.EVT_LEFT_UP, OnMainSplitterPosChanged)
        self.mainSplitterSize = None
        
        self.videoSplitter.Bind(wx.EVT_SPLITTER_DCLICK, self.OnLeftDClickVideoSplitter)
        
        def OnVideoSplitterPosChanged(event):
            sliderWindowWidth = self.videoSplitter.GetClientSize()[0] - self.videoSplitter.GetSashPosition()
            #~ sliderWindowWidth = self.videoPane.GetClientSize()[0] - self.videoSplitter.GetSashPosition()
            if True: #sliderWindowWidth - self.videoSplitter.GetSashSize() > self.videoSplitter.GetMinimumPaneSize():
                newpos = self.videoSplitter.GetSashPosition() - self.videoSplitter.GetClientSize()[0]
                #~ newpos = self.videoSplitter.GetSashPosition() - self.videoPane.GetClientSize()[0]
                self.currentScript.lastSplitSliderPos = newpos
                self.currentScript.sliderWindowShown = True
            else:
                self.currentScript.sliderWindowShown = False
            if self.zoomwindowfit:
                #~ self.ShowVideoFrame(forceRefresh=True, focus=False)
                self.ShowVideoFrame(focus=False)
            event.Skip()            
        self.videoSplitter.Bind(wx.EVT_LEFT_UP, OnVideoSplitterPosChanged)
        #~ self.videoSplitter.Bind(wx.EVT_SPLITTER_SASH_POS_CHANGED, OnVideoSplitterPosChanged)
        self.videoSplitterSize = None
        
        # Create the program's text editing notebook
        self.scriptNotebook = self.createScriptNotebook()        
        self.scriptNotebook.dblClicked = False
        #~ self.UpdateTabStyle()        
        scriptWindow = self.createScriptWindow()
        self.currentScript = scriptWindow
        self.currentSliderWindow = scriptWindow.sliderWindow
        self.scriptNotebook.AddPage(scriptWindow, self.NewFileName)        
        # Create the program's video preview window
        self.videoWindow = self.createVideoWindow(self.videoSplitter)
        
        # Create the program's menu
        shortcutList = []
        oldShortcuts = ([item[0] for item in self.options['shortcuts']], self.options['shortcuts'])        
        self.menuBackups = [1, 2] #if wx.VERSION > (2, 8) else []
        menuBar = self.createMenuBar(self.menuInfo(), shortcutList, oldShortcuts, self.menuBackups)
        self.SetMenuBar(menuBar)
        scriptWindow.contextMenu = self.menuBackups[0] if self.menuBackups else self.GetMenuBar().GetMenu(1)
        self.videoWindow.contextMenu = self.menuBackups[1] if self.menuBackups else self.GetMenuBar().GetMenu(2)
        # Add the tools to the menu
        self.createToolsMenu(shortcutList, oldShortcuts)
        # Add the macros to the menu
        self.createMacroMenu(shortcutList, oldShortcuts)
        # Set the shortcut list
        self.options['shortcuts'] = None
        self.options['shortcuts'] = shortcutList

        self.bindShortcutsToAllWindows()
        
        # Create the program's video controls
        self.videoControls = self.createVideoControls(self.programSplitter)
        spos = self.videoControls.GetClientSize().height + 6
        self.toolbarHeight = spos
        
        if wx.VERSION < (2, 9):
            self.programSplitter.SetSashSize(0)
            self.programSplitter.SplitHorizontally(self.mainSplitter, self.videoControls, -spos)
        
        # Set the minimum pane sizes
        minpanesize = 23
        mintextlines = max(0, self.options['mintextlines'])
        if mintextlines != 0:
            scrollbarheight = scriptWindow.GetSize().height - scriptWindow.GetClientSize().height
            minpanesize = minpanesize + mintextlines * self.currentScript.TextHeight(0) + scrollbarheight + 5
        self.mainSplitter.SetMinimumPaneSize(minpanesize)

        self.videoSplitter.SetMinimumPaneSize(3)
        #~ self.videoSplitter.SetMinimumPaneSize(300)
        
        # Manually implement splitter gravity (improper size updating with sub-splitters...)
        #~ self.programSplitter.SetSashGravity(1.0)
        #~ self.mainSplitter.SetSashGravity(1.0)
        #~ self.videoSplitter.SetSashGravity(1.0)
        def OnProgramSplitterSize(event):
            # programSplitter gravity
            if wx.VERSION < (2, 9):
                self.programSplitter.SetSashPosition(-self.toolbarHeight)
            
            
            # videoSplitter gravity
            if not self.separatevideowindow:
                widthSliderWindow = self.videoSplitter.GetSize()[0] - self.videoSplitter.GetSashPosition()
                #~ widthSliderWindow = self.videoPane.GetSize()[0] - self.videoSplitter.GetSashPosition()
                #~ self.videoSplitter.SetSize((self.programSplitter.GetSize()[0], -1))
                self.videoSplitter.SetSize((self.GetClientSize()[0] - self.toggleSliderWindowButton.GetSize()[0], -1))
                self.videoSplitter.SetSashPosition(-widthSliderWindow)
            
            
            
            #~ if self.currentScript.sliderWindowShown:
                #~ self.currentScript.lastSplitSliderPos = -widthSliderWindow
            # mainSplitter gravity
            if self.mainSplitter.IsSplit():
                #~ heightVideoWindow = self.mainSplitter.GetSize()[1] - self.mainSplitter.GetSashPosition()
                #~ self.mainSplitter.SetSashPosition(-heightVideoWindow)
                y = self.GetMainSplitterNegativePosition()
                self.mainSplitter.SetSashPosition(y)
                self.currentScript.lastSplitVideoPos = y
            event.Skip()
        self.programSplitter.Bind(wx.EVT_SIZE, OnProgramSplitterSize)

        if not self.separatevideowindow:
            self.mainSplitter.SplitHorizontally(self.scriptNotebook, self.videoPane)
        else:
            self.mainSplitter.SplitHorizontally(self.scriptNotebook, wx.Panel(self.mainSplitter, wx.ID_ANY))
            self.mainSplitter.Unsplit()
            # Layout the separate video window
            self.videoControls2 = self.createVideoControls(self.videoDialog, primary=False)
            self.videoStatusBar = wx.StatusBar(self.videoDialog, wx.ID_ANY)#self.videoDialog.CreateStatusBar()
            self.videoStatusBar.SetFieldsCount(2)
            self.videoStatusBar.SetStatusWidths([-1, 0])
            sizer = wx.BoxSizer(wx.VERTICAL)
            sizer.Add(self.videoPane, 1, wx.EXPAND)
            sizer.Add(self.videoControls2, 0, wx.EXPAND|wx.ALL, 0)
            sizer.Add(self.videoStatusBar, 0, wx.EXPAND)
            self.videoDialog.SetSizer(sizer)
            sizer.Layout()

            self.videoSplitter.SetSashGravity(1.0)
        
        #~ self.videoSplitter.SplitVertically(self.videoWindow, self.currentScript.sliderWindow, self.currentScript.lastSplitSliderPos)
        self.videoSplitter.SplitVertically(self.videoWindow, self.currentScript.sliderWindow, 10)
        #~ self.videoSplitter.UpdateSize()
        #~ self.videoPaneSizer.Layout()
        #~ self.videoSplitter.Unsplit()
        
        if wx.VERSION > (2, 9):
            mainFrameSizer = wx.BoxSizer(wx.VERTICAL)
            mainFrameSizer.Add(self.mainSplitter, 1, wx.EXPAND)
            mainFrameSizer.Add(self.videoControls, 0, wx.EXPAND)
            self.SetSizer(mainFrameSizer)
        
        # Hide the video preview initially
        self.HidePreviewWindow()

        # Misc
        scriptWindow.SetFocus()
        self.SetMinSize((320, 240))

    def bindShortcutsToAllWindows(self):        
        self._shortcutBindWindowDict = {self:[], self.videoWindow:[]}
        self.useEscape = False
        for label, shortcut, id in self.options['shortcuts']:
            if not shortcut:
                continue
            if shortcut.endswith('Escape'):
                self.useEscape = True
            if shortcut in self.exceptionShortcuts:
                self._shortcutBindWindowDict[self.videoWindow].append(id)
            elif shortcut != 'Escape' and shortcut in self.options['reservedshortcuts']:
                if (label, shortcut) not in self.stcShortcuts[-1]:
                    self._shortcutBindWindowDict[self.videoWindow].append(id)
            else:
                self._shortcutBindWindowDict[self].append(id)            
        self.BindShortcutsToWindows(self.options['shortcuts'])
        #~ self.BindShortcutsToWindows(self.optionsShortcuts, forcewindow=self.scrapWindow.textCtrl)
        self.scrapWindow.BindShortcuts()
        # Bind shortcuts to the video window if necessary
        if self.separatevideowindow:
            self.BindShortcutsToWindows(self.options['shortcuts'], forcewindow=self.videoWindow)
        if True:#wx.VERSION > (2, 8):
            if self.useEscape:
                self.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
                if self.separatevideowindow:
                    self.videoWindow.Bind(wx.EVT_CHAR_HOOK, self.OnCharHook)
            else:
                self.Unbind(wx.EVT_CHAR_HOOK)
                if self.separatevideowindow:
                    self.videoWindow.Unbind(wx.EVT_CHAR_HOOK)

    def menuInfo(self):
        self.exceptionShortcuts = [
            'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
            'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
            '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
            'Enter', 'Space', 'Insert', 'Backspace', 'Delete', 
            'Home', 'End', 'PgUp', 'PgDn', 'Up', 'Down', 'Left', 'Right',
            'Numpad 0', 'Numpad 1', 'Numpad 2', 'Numpad 3', 'Numpad 4', 'Numpad 5', 'Numpad 6', 'Numpad 7', 'Numpad 8', 'Numpad 9',
            'Numpad +', 'Numpad -', 'Numpad *', 'Numpad /', 'Numpad .', 'Numpad Enter',
            '`', '-', '=', '\\', '[', ']', ';', "'", ',', '.', '/',
            '~', '!', '@', '#', '$', '%', '^', '&', '*', '(', ')', '_', '+', '|', '{', '}', ':', '"', '<', '>', '?',
        ]
        self.stcShortcuts = [
            ('Shift+Down',          _('Extend selection to line down position')),
            ('Ctrl+Down',           _('Scroll down')),
            ('Alt+Shift+Down',      _('Extend rectangular selection to line down position')),
            ('Shift+Up',            _('Extend selection to line up position')),
            ('Ctrl+Up',             _('Scroll up')),
            ('Alt+Shift+Up',        _('Extend rectangular selection to line up position')),
            ('Ctrl+[',			    _('Go to previous paragraph')),
            ('Ctrl+Shift+[',		_('Extend selection to previous paragraph')),
            ('Ctrl+]',			    _('Go to next paragraph')),
            ('Ctrl+Shift+]',		_('Extend selection to next paragraph')),
            ('Shift+Left',		    _('Extend selection to previous character')),
            ('Ctrl+Left',		    _('Go to previous word')),
            ('Ctrl+Shift+Left',	    _('Extend selection to previous word')),
            ('Alt+Shift+Left',	    _('Extend rectangular selection to previous character')),
            ('Shift+Right',		    _('Extend selection to next character')),
            ('Ctrl+Right',		    _('Go to next word')),
            ('Ctrl+Shift+Right',	_('Extend selection to next word')),
            ('Alt+Shift+Right',	    _('Extend rectangular selection to next character')),
            ('Ctrl+/',		        _('Go to previous word part')),
            ('Ctrl+Shift+/',		_('Extend selection to previous word part')),
            ('Ctrl+\\',		        _('Go to next word part')),
            ('Ctrl+Shift+\\',	    _('Extend selection to next word part')),
            ('Shift+Home', 		    _('Extend selection to start of line')),
            ('Ctrl+Home', 		    _('Go to start of document')),
            ('Ctrl+Shift+Home', 	_('Extend selection to start of document')),
            ('Alt+Home', 		    _('Go to start of line')),
            ('Alt+Shift+Home', 	    _('Extend selection to start of line')),
            ('Shift+End', 		    _('Extend selection to end of line')),
            ('Ctrl+End', 		    _('Go to end of document')),
            ('Ctrl+Shift+End', 	    _('Extend selection to end of document')),
            ('Alt+End', 		    _('Go to end of line')),
            ('Alt+Shift+End', 	    _('Extend selection to end of line')),
            ('Shift+PgUp',		    _('Extend selection to previous page')),
            ('Alt+Shift+PgUp',	    _('Extend rectangular selection to previous page')),
            ('Shift+PgDn',		    _('Extend selection to next page')),
            ('Alt+Shift+PgDn',	    _('Extend rectangular selection to next page')),
            ('Shift+Delete',        _('Cut')),
            ('Ctrl+Delete',         _('Delete to end of word')),
            ('Ctrl+Shift+Delete',   _('Delete to end of line')),
            ('Shift+Insert',  	    _('Paste')),
            ('Ctrl+Insert',  	    _('Copy')),
            ('Shift+Backspace',	    _('Delete back')),
            ('Ctrl+Backspace',      _('Delete to start of word')),
            ('Alt+Backspace',       _('Undo')),
            ('Ctrl+Shift+Backspace',_('Delete to start of line')),
            ('Ctrl+Z', 			    _('Undo')),
            ('Ctrl+Y', 			    _('Redo')),
            ('Ctrl+X', 			    _('Cut')),
            ('Ctrl+C', 			    _('Copy')),
            ('Ctrl+V', 			    _('Paste')),
            ('Ctrl+A', 			    _('Select all')),
            ('Escape',              _('Cancel autocomplete or calltip')),
            ('Tab',		            _('Indent selection')),
            ('Shift+Tab',		    _('Unindent selection')),
            ('Shift+Return',        _('Newline')),
            ('Ctrl+Numpad +', 	    _('Zoom in')),
            ('Ctrl+Numpad -', 	    _('Zoom out')),
            ('Ctrl+Numpad /', 	    _('Reset zoom level to normal')),
            ('Ctrl+L', 			    _('Line cut')),
            ('Ctrl+Shift+L', 	    _('Line delete')),
            ('Ctrl+Shift+T', 	    _('Line copy')),
            ('Ctrl+T', 			    _('Transpose line with the previous')),
            ('Ctrl+D', 			    _('Line or selection duplicate')),
            ('Ctrl+U', 			    _('Convert selection to lowercase')),
            ('Ctrl+Shift+U', 	    _('Convert selection to uppercase')),
            (
            ('Edit -> Indent selection', 'Tab'),
            ('Edit -> Unindent selection', 'Shift+Tab'),
            ('Edit -> Undo', 'Ctrl+Z'),
            ('Edit -> Redo', 'Ctrl+Y'),
            ('Edit -> Cut', 'Ctrl+X'),
            ('Edit -> Copy', 'Ctrl+C'),
            ('Edit -> Paste', 'Ctrl+V'),
            ('Edit -> Select All', 'Ctrl+A'),
            ),
        ] 
        self.menuBookmark = self.createMenu(
            (
                (''), 
                (_('sort ascending'), '', self.UpdateBookmarkMenu, _('Sort bookmarks ascending'), wx.ITEM_CHECK, True),
                (_('show time'), '', self.UpdateBookmarkMenu, _('Show bookmarks with timecode'), wx.ITEM_CHECK, False),
                (_('show title'), '', self.UpdateBookmarkMenu, _('Show bookmarks with title'), wx.ITEM_CHECK, True),
            )
        )
        self.yuv2rgbDict = {
            _('Rec601'): 'Rec601',
            _('PC.601'): 'PC.601',
            _('Rec709'): 'Rec709',
            _('PC.709'): 'PC.709',
            _('Progressive'): 'Progressive',
            _('Interlaced'): 'Interlaced',
            _('Swap UV'): 'swapuv',
        }
        reverseMatrixDict = dict([(v,k) for k,v in self.yuv2rgbDict.items()])
        self.zoomLabelDict = {
            _('25%'): '25',
            _('50%'): '50',
            _('100% (normal)'): '100',
            _('200%'): '200',
            _('300%'): '300',
            _('400%'): '400',
            _('Fill window'): 'fill',
            _('Fit inside window'): 'fit',
        }
        reverseZoomLabelDict = dict([(v,k) for k,v in self.zoomLabelDict.items()])
        self.flipLabelDict = {
            _('Vertically'): 'flipvertical',
            _('Horizontally'): 'fliphorizontal',
        }
        return (
            (_('&File'),
                (_('New tab'), 'Ctrl+N', self.OnMenuFileNew, _('Create a new tab')),
                (_('Open...'), 'Ctrl+O', self.OnMenuFileOpen, _('Open an existing script')),
                (_('Close tab'), 'Ctrl+W', self.OnMenuFileClose, _('Close the current tab')),
                (_('Close all tabs'), 'Ctrl+Shift+W', self.OnMenuFileCloseAllTabs, _('Close every tab')),
                (_('Rename tab'), '', self.OnMenuFileRenameTab, _('Rename the current tab. If script file is existing, also rename it')),
                (_('Save script'), 'Ctrl+S', self.OnMenuFileSaveScript, _('Save the current script')),
                (_('Save script as...'), 'Ctrl+Shift+S', self.OnMenuFileSaveScriptAs, _('Choose where to save the current script')),
                (''),
                (_('Load session...'), 'Alt+O', self.OnMenuFileLoadSession, _('Load a session into the tabs')),
                (_('Save session...'), 'Alt+S', self.OnMenuFileSaveSession, _('Save all the scripts as a session, including slider info')),
                (_('Backup current session'), 'Alt+B', self.OnMenuFileBackupSession, _('Backup the current session for next program run')),
                (''),
                #~ (_('Export filter customizations...'), '', self.OnMenuFileExportFilters, _('Export filter customizations for sharing purposes')),
                #~ (_('Import filter customizations...'), '', self.OnMenuFileImportFilters, _('Import filter customizations from an exported file')),
                #~ (''),
                (_('Next tab'), 'Ctrl+Tab', self.OnMenuFileNextTab, _('Switch to next script tab')),
                (_('Previous tab'), 'Ctrl+Shift+Tab', self.OnMenuFilePrevTab, _('Switch to previous script tab')),
                (''),
                (_('Toggle scrap window'), 'Ctrl+P', self.OnMenuEditShowScrapWindow, _('Show the scrap window')),
                (''),
                (''),
                (_('&Exit'), 'Alt+X', self.OnMenuFileExit, _('Exit the program')),
            ),
            (_('&Edit'),
                (_('Undo'), 'Ctrl+Z', self.OnMenuEditUndo, _('Undo last text operation')),
                (_('Redo'), 'Ctrl+Y', self.OnMenuEditRedo, _('Redo last text operation')),
                (''),
                (_('Cut'), 'Ctrl+X', self.OnMenuEditCut, _('Cut the selected text')),
                (_('Copy'), 'Ctrl+C', self.OnMenuEditCopy, _('Copy the selected text')),
                (_('Paste'), 'Ctrl+V', self.OnMenuEditPaste, _('Paste the selected text')),
                (''),
                (_('Find...'), 'Ctrl+F', self.OnMenuEditFind, _('Open a find text dialog box')),
                (_('Find next'), 'F3', self.OnMenuEditFindNext, _('Find the next instance of given text')),
                (_('Replace...'), 'Ctrl+H', self.OnMenuEditReplace, _('Open a replace text dialog box')),
                (''),
                (_('Select All'), 'Ctrl+A', self.OnMenuEditSelectAll, _('Select all the text')),
                (''),
                (_('&Insert'),
                    (
                    (_('Insert source...'), 'F9', self.OnMenuEditInsertSource, _('Choose a source file to insert into the text')),
                    (_('Insert filename...'), 'Shift+F9', self.OnMenuEditInsertFilename, _('Get a filename from a dialog box to insert into the text')),
                    (_('Insert plugin...'), 'F10', self.OnMenuEditInsertPlugin, _('Choose a plugin dll to insert into the text')),
                    (''),
                    (_('Insert user slider...'), 'F12', self.OnMenuEditInsertUserSlider, _('Insert a user-scripted slider into the text')),
                    (_('Insert user slider separator'), 'Shift+F12', self.OnMenuEditInsertUserSliderSeparator, _('Insert a tag which indicates a separator in the user slider window')),
                    (''),
                    (_('Insert frame #'), 'F11', self.OnMenuEditInsertFrameNumber, _('Insert the current frame number into the text')),
                    (''),
                    (_('Tag selection for toggling'), 'Ctrl+T', self.OnMenuEditToggleTagSelection, _('Add tags surrounding the selected text for toggling with the video preview')),
                    (_('Clear all tags'), 'Ctrl+Shift+T', self.OnMenuEditClearToggleTags, _('Clear all toggle tags from the text')),
                    ),
                ),
                (''),
                (_('Indent selection'), 'Tab', self.OnMenuEditIndentSelection, _('Indent the selected lines')),
                (_('Unindent selection'), 'Shift+Tab', self.OnMenuEditUnIndentSelection, _('Unindent the selected lines')),
                (_('Block comment'), 'Ctrl+Q', self.OnMenuEditBlockComment, _('Comment or uncomment selected lines')),
                (_('Style comment'), 'Alt+Q', self.OnMenuEditStyleComment, _('Comment at start of a text style or uncomment')),
                (_('Toggle current fold'), '', self.OnMenuEditToggleCurrentFold, _('Toggle the fold point On/OFF at the current line')),
                (_('Toggle all folds'), '', self.OnMenuEditToggleAllFolds, _('Toggle all fold points On/OFF')),
                (''),
                (_('&AviSynth function'),
                    (
                    (_('Autocomplete'), 'Ctrl+Space', self.OnMenuEditAutocomplete, _('Show list of filternames matching the partial text at the cursor')),
                    (_('Autocomplete all'), 'Alt+Space', self.OnMenuEditAutocompleteAll, _("Disregard user's setting, show full list of filternames matching the partial text at the cursor")),
                    (_('Show calltip'), 'Ctrl+Shift+Space', self.OnMenuEditShowCalltip, _('Show the calltip for the filter (only works if cursor within the arguments)')),
                    (_('Show function definition'), 'Ctrl+Shift+D', self.OnMenuEditShowFunctionDefinition, _('Show the AviSynth function definition dialog for the filter')),
                    (_('Filter help file'), 'Shift+F1', self.OnMenuEditFilterHelp, _("Run the help file for the filter (only works if cursor within the arguments or name is highlighted)")),
                    ),
                ),
                (''),
                (_('&Miscellaneous'),
                    (
                    (_('Move line up'), 'Ctrl+Shift+Up', self.OnMenuEditMoveLineUp, _('Move the current line or selection up by one line')),
                    (_('Move line down'), 'Ctrl+Shift+Down', self.OnMenuEditMoveLineDown, _('Move the current line or selection down by one line')),
                    (''),
                    (_('Copy unmarked script to clipboard'), 'Ctrl+Shift+C', self.OnMenuCopyUnmarkedScript, _('Copy the current script without any AvsP markings (user-sliders, toggle tags) to the clipboard')),
                    (_('Copy avisynth error to clipboard'), '', self.OnMenuCopyAvisynthError, _('Copy the avisynth error message shown on the preview window to the clipboard')),
                    #~(_('Copy status bar to clipboard'), '', self.OnMenuCopyStatusBar, _('Copy the message shown on the status bar to the clipboard')),
                    ),
                ),
            ),
            (_('&Video'),
                (_('Add/Remove bookmark'), 'Ctrl+B', self.OnMenuVideoBookmark, _('Mark the current frame on the frame slider')),
                (_('Clear all bookmarks'), '', self.OnMenuVideoGotoClearAll, _('Clear all bookmarks')),
                (_('Titled &bookmarks'),
                    (
                    (_('Move titled bookmark'), 'Ctrl+M', self.OnMenuVideoBookmarkMoveTitle, _('Move the nearest titled bookmark to the current position. A historic title will be restored if it matches the condition.')),
                    (_('Restore historic titles'), '', self.OnMenuVideoBookmarkRestoreHistory, _('Restore all historic titles')),
                    (_('Clear historic titles'), '', self.OnMenuVideoBookmarkClearHistory, _('Clear all historic titles')),
                    (_('Set title (auto)'), '', self.OnMenuVideoBookmarkAutoTitle, _("Generate titles for untitled bookmarks by the pattern - 'Chapter %02d'")),
                    (_('Set title (manual)'), '', self.OnMenuVideoBookmarkSetTitle, _('Edit title for bookmarks in a list table')),
                    ),
                ),
                (''),
                (_('&Navigate'),
                    (
                    (_('Go to &bookmark'), self.menuBookmark, -1),
                    (_('Next bookmark'), 'F2', self.OnMenuVideoGotoNextBookmark, _('Go to next bookmarked frame')),
                    (_('Previous bookmark'), 'Shift+F2', self.OnMenuVideoGotoPreviousBookmark, _('Go to previous bookmarked frame')),
                    (''),
                    (_('Forward 1 frame'), 'Right', self.OnMenuVideoNextFrame, _('Show next video frame (keyboard shortcut active when video window focused)'), wx.ITEM_NORMAL, None, self.videoWindow),
                    (_('Backward 1 frame'), 'Left', self.OnMenuVideoPrevFrame, _('Show previous video frame (keyboard shortcut active when video window focused)'), wx.ITEM_NORMAL, None, self.videoWindow),
                    (_('Forward 1 second'), 'Down', self.OnMenuVideoNextSecond, _('Show video 1 second forward (keyboard shortcut active when video window focused)'), wx.ITEM_NORMAL, None, self.videoWindow),
                    (_('Backward 1 second'), 'Up', self.OnMenuVideoPrevSecond, _('Show video 1 second back (keyboard shortcut active when video window focused)'), wx.ITEM_NORMAL, None, self.videoWindow),
                    (_('Forward 1 minute'), 'PgDn', self.OnMenuVideoNextMinute, _('Show video 1 minute forward (keyboard shortcut active when video window focused)'), wx.ITEM_NORMAL, None, self.videoWindow),
                    (_('Backward 1 minute'), 'PgUp', self.OnMenuVideoPrevMinute, _('Show video 1 minute back (keyboard shortcut active when video window focused)'), wx.ITEM_NORMAL, None, self.videoWindow),
                    (''),
                    (_('Forward x units'), '', self.OnMenuVideoNextCustomUnit, _('Jump forward by x units (you can specify x in the options dialog)')),
                    (_('Backwards x units'), '', self.OnMenuVideoPrevCustomUnit, _('Jump backwards by x units (you can specify x in the options dialog)')),
                    (''),
                    (_('Go to first frame'), '', self.OnMenuVideoFirstFrame, _('Go to first video frame (keyboard shortcut active when video window focused)'), wx.ITEM_NORMAL, None, self.videoWindow),
                    (_('Go to last frame'), '', self.OnMenuVideoLastFrame, _('Go to last video frame (keyboard shortcut active when video window focused)'), wx.ITEM_NORMAL, None, self.videoWindow),
                    (''),
                    (_('Last scrolled frame'), 'F8', self.OnMenuVideoGotoLastScrolled, _('Go to last scrolled frame')),
                    (''),
                    (_('Go to frame...'), 'Ctrl+G', self.OnMenuVideoGoto, _('Enter a video frame or time to jump to')),
                    ),
                ),
                (''),
                (_('Crop editor...'), '', self.OnMenuVideoCropEditor, _('Show the crop editor dialog')),
                (_('&Trim selection editor'),
                    (
                    (_('Show trim selection editor'), '', self.OnMenuVideoTrimEditor, _('Show the trim selection editor dialog')),
                    (''),
                    (_('Set selection startpoint'), 'Home', self.OnMenuVideoTrimEditorSetStartpoint, _('Set a selection startpoint (shows the trim editor if not visible)'), wx.ITEM_NORMAL, None, self.videoWindow),
                    (_('Set selection endpoint'), 'End', self.OnMenuVideoTrimEditorSetEndpoint, _('Set a selection endpoint (shows the trim editor if not visible)'), wx.ITEM_NORMAL, None, self.videoWindow),
                    ),
                ),
                (''),
                (_('&Zoom'),
                    (
                    (reverseZoomLabelDict['25'], '', self.OnMenuVideoZoom, _('Zoom video preview to 25%'), wx.ITEM_RADIO, False),
                    (reverseZoomLabelDict['50'], '', self.OnMenuVideoZoom, _('Zoom video preview to 50%'), wx.ITEM_RADIO, False),
                    (reverseZoomLabelDict['100'], 'Numpad /', self.OnMenuVideoZoom, _('Zoom video preview to 100% (normal)'), wx.ITEM_RADIO, True),
                    (reverseZoomLabelDict['200'], '', self.OnMenuVideoZoom, _('Zoom video preview to 200%'), wx.ITEM_RADIO, False),
                    (reverseZoomLabelDict['300'], '', self.OnMenuVideoZoom, _('Zoom video preview to 300%'), wx.ITEM_RADIO, False),
                    (reverseZoomLabelDict['400'], '', self.OnMenuVideoZoom, _('Zoom video preview to 400%'), wx.ITEM_RADIO, False),
                    (reverseZoomLabelDict['fill'], '', self.OnMenuVideoZoom, _('Zoom video preview to fill the entire window'), wx.ITEM_RADIO, False),
                    (reverseZoomLabelDict['fit'], '', self.OnMenuVideoZoom, _('Zoom video preview to fit inside the window'), wx.ITEM_RADIO, False),
                    (''),
                    (_('Zoom in'), 'Numpad +', self.OnZoomInOut, _("Enlarge preview image to next zoom level. Not work under 'Fill window' or 'Fit inside window'")),
                    (_('Zoom out'), 'Numpad -', self.OnZoomInOut, _("Shrink preview image to previous zoom level. Not work under 'Fill window' or 'Fit inside window'")),
                    ),
                ),
                (_('&Flip'),
                    (
                    (_('Vertically'), '', self.OnMenuVideoFlip, _('Flip video preview upside down'), wx.ITEM_CHECK, False),
                    (_('Horizontally'), '', self.OnMenuVideoFlip, _('Flip video preview from left to right'), wx.ITEM_CHECK, False),
                    ),
                ),
                (_('&YUV -> RGB'),
                    (
                    (reverseMatrixDict['swapuv'], '', self.OnMenuVideoYUV2RGB, _('Swap chroma channels (U and V)'), wx.ITEM_CHECK, False),
                    (''),
                    (reverseMatrixDict['Rec601'], '', self.OnMenuVideoYUV2RGB, _('For YUV source, assume it is Rec601 (default)'), wx.ITEM_RADIO, True),
                    (reverseMatrixDict['PC.601'], '', self.OnMenuVideoYUV2RGB, _('For YUV source, assume it is PC.601'), wx.ITEM_RADIO, False),
                    (reverseMatrixDict['Rec709'], '', self.OnMenuVideoYUV2RGB, _('For YUV source, assume it is Rec709'), wx.ITEM_RADIO, False),
                    (reverseMatrixDict['PC.709'], '', self.OnMenuVideoYUV2RGB, _('For YUV source, assume it is PC.709'), wx.ITEM_RADIO, False),
                    (''),
                    (reverseMatrixDict['Progressive'], '', self.OnMenuVideoYUV2RGB, _('For YV12 only, assume it is progressive (default)'), wx.ITEM_RADIO, True),
                    (reverseMatrixDict['Interlaced'], '', self.OnMenuVideoYUV2RGB, _('For YV12 only, assume it is interlaced'), wx.ITEM_RADIO, False),
                    ),
                ),
                (''),
                (_('Save image as...'), '', self.OnMenuVideoSaveImage, _('Save the current frame as a bitmap')),
                (''),
                (_('Refresh preview'), 'F5', self.OnMenuVideoRefresh, _('Force the script to reload and refresh the video frame')),
                (_('Show/Hide the preview'), 'Shift+F5', self.OnMenuVideoToggle, _('Toggle the video preview')),
                (_('Release all videos from memory'), '', self.OnMenuVideoReleaseMemory, _('Release all open videos from memory')),
                (_('Switch video/text focus'), 'Escape', self.OnMenuVideoSwitchMode, _('Switch focus between the video preview and the text editor')),
                (_('Toggle the slider sidebar'), 'Alt+F5', self.OnMenuVideoToggleSliderWindow, _('Show/hide the slider sidebar (double-click the divider for the same effect)')),
                (_('External player'), 'F6', self.OnMenuVideoExternalPlayer, _('Play the current script in an external program')),
                (''),
                (_('Video information'), '', self.OnMenuVideoInfo, _('Show information about the video in a dialog box')),
            ),
            (_('&Options'),
                (_('Always on top'), '', self.OnMenuOptionsAlwaysOnTop, _('Keep this window always on top of others'), wx.ITEM_CHECK, self.options['alwaysontop']),
                #~(_('Only allow a single instance'), '', self.OnMenuOptionsSingleInstance, _('Only allow a single instance of AvsP'), wx.ITEM_CHECK, self.options['singleinstance']),
                #~(_('Use monospaced font'), '', self.OnMenuOptionsMonospaceFont, _('Override all fonts to use a specified monospace font'), wx.ITEM_CHECK, self.options['usemonospacedfont']),
                (_('Disable video preview'), '', self.OnMenuOptionsDisablePreview, _('If checked, the video preview will not be shown under any circumstances'), wx.ITEM_CHECK, self.options['disablepreview']),
                #~(_('Enable paranoia mode'), '', self.OnMenuOptionsEnableParanoiaMode, _('If checked, the current session is backed up prior to previewing any new script'), wx.ITEM_CHECK, self.options['paranoiamode']),
                #~(_('Enable line-by-line update'), '', self.OnMenuOptionsEnableLineByLineUpdate, _('Enable the line-by-line video update mode (update every time the cursor changes line position)'), wx.ITEM_CHECK, self.options['autoupdatevideo']),
                (''),
                (_('Associate .avs files with AvsP'), '', self.OnMenuOptionsAssociate, _('Configure this computer to open .avs files with AvsP when double-clicked')),
                (''),
                (_('AviSynth function definition...'), '', self.OnMenuOptionsFilters, _('Add or override AviSynth functions in the database')),
                #~ (_('AviSynth function definition...'), '', self.OnMenuOptionsFilters, _('Edit the AviSynth function info for syntax highlighting and calltips')),
                (_('Fonts and colors...'), '', self.OnMenuOptionsFontsAndColors, _('Edit the various AviSynth script fonts and colors')),
                (_('Extension templates...'), '', self.OnMenuOptionsTemplates, _('Edit the extension-based templates for inserting sources')),
                (''),
                (_('Keyboard shortcuts...'), '', self.OnMenuConfigureShortcuts, _('Configure the program keyboard shortcuts')),
                (_('Program settings...'), '', self.OnMenuOptionsSettings, _('Configure program settings')),
            ),
            (_('&Help'),
                (_('Animated tutorial'), '', self.OnMenuHelpAnimatedTutorial, _('View an animated tutorial for AvsP (from the AvsP website)')),
                (''),
                (_('Text features'), '', self.OnMenuHelpTextFeatures, _('Learn more about AvsP text features (from the AvsP website)')),
                (_('Video features'), '', self.OnMenuHelpVideoFeatures, _('Learn more about AvsP video features (from the AvsP website)')),
                (_('User sliders'), '', self.OnMenuHelpUserSliderFeatures, _('Learn more about AvsP user sliders (from the AvsP website)')),
                (_('Macros'), '', self.OnMenuHelpMacroFeatures, _('Learn more about AvsP macros (from the AvsP website)')),
                (''),
                (_('Avisynth help'), 'F1', self.OnMenuHelpAvisynth, _('Open the avisynth help html')),
                (_('Open Avisynth plugins folder'), '', self.OnMenuHelpAvisynthPlugins, _('Open the avisynth plugins folder')),
                (''),
                (_('About AvsPmod'), '', self.OnMenuHelpAbout, _('About this program')),
            ),
        )

    def buttonInfo(self):
        bmpPlay = wx.BitmapFromImage(play_icon.getImage().Scale(16,16))
        self.bmpRightTriangle = spin_icon.GetBitmap() #wx.BitmapFromImage(play_icon.getImage().Scale(10,10))
        self.bmpLeftTriangle = self.bmpRightTriangle.ConvertToImage().Mirror().ConvertToBitmap()
        bmpRight = wx.BitmapFromImage(next_icon.getImage().Scale(16,16))
        bmpLeft = bmpRight.ConvertToImage().Mirror().ConvertToBitmap()
        self.bmpVidUp = bmpPlay.ConvertToImage().Rotate90(False).ConvertToBitmap()
        self.bmpVidDown = bmpPlay.ConvertToImage().Rotate90().ConvertToBitmap()
        bmpSkipRight = wx.BitmapFromImage(skip_icon.getImage().Scale(16,16))
        bmpSkipLeft = bmpSkipRight.ConvertToImage().Mirror().ConvertToBitmap()

        return (
            (self.bmpVidUp, self.OnMenuVideoToggle, _('Toggle the video preview')),
            (bmpSkipLeft, self.OnMenuVideoGotoPreviousBookmark,_('Previous bookmark')),
            (bmpLeft, self.OnMenuVideoPrevFrame, _('Previous frame')),
            (bmpRight, self.OnMenuVideoNextFrame, _('Next frame')),
            (bmpSkipRight, self.OnMenuVideoGotoNextBookmark,_('Next bookmark')),
            (bmpPlay, self.OnMenuVideoExternalPlayer, _('Run the script with an external program')),
        )

    def createToolsMenu(self, shortcutList, oldShortcuts):
        menuInfo = []
        self.toolsImportNames = {}
        appendedList = ['toolsmenu']
        # First add items defined by ToolsMenu.py
        try:
            items = __import__('ToolsMenu').menuInfo
        except ImportError:
            items = []
        for item in items:
            if len(item) == 3:
                importName, menuLabel, statusString = item
                id = wx.NewId()
                self.toolsImportNames[id] = importName
                appendedList.append(importName.lower())
                menuInfo.append((menuLabel, '', self.OnMenuToolsRunSelected, statusString, id))
            else:
                menuInfo.append('')
        baseSize = len(menuInfo)
        # Then add any additional python files
        if os.path.isdir(self.toolsfolder):
            namelist = os.listdir(self.toolsfolder)
            namelist.sort()
            for name in namelist:
                root, ext = os.path.splitext(name)
                if ext.lower().startswith('.py') and root.lower() not in appendedList:
                    f = open(os.path.join(self.toolsfolder, name))
                    text = f.read()
                    f.close()
                    if not re.findall(r'\bdef\s+avsp_run\s*\(\):', text):
                        continue
                    splitroot = root.split(']',1)
                    if len(splitroot) == 2 and root.startswith('['):
                        menuLabel = splitroot[1].strip()
                    else:
                        menuLabel = root
                    if len(menuInfo) == baseSize:
                        menuInfo.append('')
                    if menuLabel.strip().startswith('---'):
                        menuInfo.append('')
                    else:
                        id = wx.NewId()
                        self.toolsImportNames[id] = root
                        appendedList.append(root.lower())
                        menuInfo.append((menuLabel, '', self.OnMenuToolsRunSelected, _('Run the selected tool'), id))
        if len(menuInfo) == 0:
            menuInfo.append((''))
        menu = self.createMenu(menuInfo, _('&Tools'), shortcutList, oldShortcuts)
        self.toolsMenuPos = 3
        self.GetMenuBar().Insert(self.toolsMenuPos, menu, _('&Tools'))

    def createMacroMenu(self, shortcutList, oldShortcuts):
        menuInfo = []
        self.macrosImportNames = {}
        self.macrosStack = []
        if os.path.isdir(self.macrofolder):
            def createMenuList(menuList, namelist, dirname):
                namelist.sort()
                for name in namelist:
                    fullname = os.path.join(dirname, name)
                    if os.path.isdir(fullname):
                        submenuList = []
                        createMenuList(submenuList, os.listdir(fullname), fullname)
                        if submenuList:
                            splitname = name.split(']',1)
                            if len(splitname) == 2 and name.startswith('['):
                                name = splitname[1].strip()
                            menuList.append((name, submenuList))
                for name in namelist:
                    fullname = os.path.join(dirname, name)
                    root, ext = os.path.splitext(name)
                    if ext.lower() == '.py':
                        splitroot = root.split(']',1)
                        if len(splitroot) == 2 and root.startswith('['):
                            root = splitroot[1].strip()
                        if root.strip().startswith('---'):
                            menuList.append('')
                        else:
                            id = wx.NewId()
                            self.macrosImportNames[id] = fullname
                            if root.strip().startswith('ccc'):
                                root = root.strip()[3:].strip()
                                if not root:
                                    root = self.getMacrosLabelFromFile(fullname)
                                menuList.append((root, '', self.OnMenuMacroRunSelected, _('a macro check item'), (wx.ITEM_CHECK, False, id)))
                            elif root.strip().startswith('CCC'):
                                root = root.strip()[3:].strip()
                                if not root:
                                    root = self.getMacrosLabelFromFile(fullname)
                                menuList.append((root, '', self.OnMenuMacroRunSelected, _('a macro check item'), (wx.ITEM_CHECK, True, id)))
                            elif root.strip().startswith('rrr'):
                                if not root:
                                    root = self.getMacrosLabelFromFile(fullname)
                                root = root.strip()[3:].strip()
                                menuList.append((root, '', self.OnMenuMacroRunSelected, _('a macro radio item'), (wx.ITEM_RADIO, False, id)))
                            elif root.strip().startswith('RRR'):
                                if not root:
                                    root = self.getMacrosLabelFromFile(fullname)
                                root = root.strip()[3:].strip()
                                menuList.append((root, '', self.OnMenuMacroRunSelected, _('a macro radio item'), (wx.ITEM_RADIO, True, id)))
                            else:
                                if not root:
                                    root = self.getMacrosLabelFromFile(fullname)
                                menuList.append((root, '', self.OnMenuMacroRunSelected, _('Run selected macro'), id))
            createMenuList(menuInfo, os.listdir(self.macrofolder), self.macrofolder)

            menuInfo.append((''))
            menuInfo.append(('macros_readme.txt', '', self.OnMenuMacrosReadme, _('View the readme for making macros')))
            menuInfo.append(('Open macros folder', '', self.OnMenuMacrosFolder, _('Open the macros folder')))
        else:
            menuInfo.append((''))
        menu = self.createMenu(menuInfo, _('&Macros'), shortcutList, oldShortcuts)
        self.macroMenuPos = 4
        self.GetMenuBar().Insert(self.macroMenuPos, menu, _('&Macros'))

    def createScriptNotebook(self):
        # Create the notebook
        style = wx.NO_BORDER
        if self.options['multilinetab']:
            style |= wx.NB_MULTILINE
        if self.options['fixedwidthtab']:
            style |= wx.NB_FIXEDWIDTH
        nb = wx.Notebook(self.mainSplitter, wx.ID_ANY, style=style)
        # Create the right-click menu
        menuInfo = (
            (_('Close'), '', self.OnMenuFileClose),
            (_('Rename'), '', self.OnMenuFileRenameTab),
            (''),
            (_('Save'), '', self.OnMenuFileSaveScript),
            (_('Save as...'), '', self.OnMenuFileSaveScriptAs),
            (''),
            (_('Select all'), '', self.OnMenuEditSelectAll),
            (''),
            (_('Copy to new tab'), '', self.OnMenuEditCopyToNewTab),
            (_('Reposition to'), 
                (
                (''),
                ),
            ),
        )
        menu = self.createMenu(menuInfo)
        nb.contextMenu = menu
        if self.options['usetabimages']:
            color1 = wx.SystemSettings.GetColour(wx.SYS_COLOUR_SCROLLBAR)
            #~ color1 = wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNSHADOW)
            color2 = wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DDKSHADOW)
            color3 = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW)
            color4 = wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT)
            # Create the mask
            w = h = 15
            bmpMask = wx.EmptyBitmap(w, h)
            mdc = wx.MemoryDC()
            mdc.SelectObject(bmpMask)
            mdc.DrawRoundedRectangle(0,0,w,h,3)
            mdc = None
            mask = wx.Mask(bmpMask)
            # Create the bitmap
            bmpBase = wx.EmptyBitmap(w, h)
            bmpBase.SetMask(mask)
            mdc = wx.MemoryDC()
            mdc.SelectObject(bmpBase)
            mdc.SetBackground(wx.Brush(color1))
            mdc.Clear()
            mdc.SetPen(wx.Pen(color2))
            mdc.SetBrush(wx.Brush(color2))
            mdc.DrawPolygon([wx.Point(0,h), wx.Point(w,h), wx.Point(w,0)])
            mdc.SetPen(wx.Pen(color3))
            mdc.SetBrush(wx.Brush(color3))
            th = 3
            mdc.DrawRoundedRectangle(th,th,w-2*th,h-2*th,0)
            mdc = None
            imageBase = bmpBase.ConvertToImage()
            il = wx.ImageList(w, h)
            for i in xrange(10):
                bmp = wx.BitmapFromImage(imageBase)
                mdc = wx.MemoryDC()
                mdc.SelectObject(bmp)
                mdc.SetTextForeground(color4)
                #~ mdc.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName='terminal'))
                #~ mdc.DrawText(str(i+1), 4,4)
                #~ mdc.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName='verdana'))
                #~ mdc.DrawText(str(i+1), 4,0)
                mdc.SetFont(wx.Font(8, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName='courier new'))
                mdc.DrawText(str((i+1) % 10), 4,0)
                mdc = None
                il.Add(bmp)
            nb.AssignImageList(il)
        # Event binding
        nb.Bind(wx.EVT_MIDDLE_DOWN, self.OnMiddleDownNotebook)
        nb.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDownNotebook)
        nb.Bind(wx.EVT_LEFT_UP, self.OnLeftUpNotebook)
        nb.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClickNotebook)
        nb.Bind(wx.EVT_RIGHT_UP, self.OnRightClickNotebook)
        nb.Bind(wx.EVT_MOTION, self.OnMouseMotionNotebook)
        nb.Bind(wx.EVT_LEAVE_WINDOW, self.OnLeftUpNotebook)
        nb.Bind(wx.EVT_FIND, AvsStyledTextCtrl.OnFindPressed)
        nb.Bind(wx.EVT_FIND_NEXT, AvsStyledTextCtrl.OnFindPressed)
        nb.Bind(wx.EVT_FIND_REPLACE, AvsStyledTextCtrl.OnReplacePressed)
        nb.Bind(wx.EVT_FIND_REPLACE_ALL, AvsStyledTextCtrl.OnReplaceAllPressed)
        nb.Bind(wx.EVT_FIND_CLOSE, AvsStyledTextCtrl.OnFindClose)
        return nb

    def createScriptWindow(self):
        # Create the instance of the window
        scriptWindow = AvsStyledTextCtrl(self.scriptNotebook, self, style=wx.STATIC_BORDER,
            #~ filterDict=self.optionsFilters,
            #~ filterPresetDict=self.options['filterpresets'],
            #~ keywordLists=self.optionsAvsKeywords,
            #~ autocomplete=self.options['autocomplete'],
            #~ autoparentheses=self.options['autoparentheses'],
            #~ usestringeol=self.options['usestringeol'],
            #~ syntaxhighlight=self.options['syntaxhighlight'],
            #~ calltips=self.options['calltips'],
            #~ frequentcalltips=self.options['frequentcalltips'],
            #~ usecustomlexer=True, #self.options['usecustomlexer'],
            #~ usetabs=self.options['usetabs'],
            #~ tabwidth=self.options['tabwidth'],
            #~ wrap=self.options['wrap'],
            #~ highlightline=self.options['highlightline'],
            #~ highlightlinecolor=self.options['highlightlinecolor'],
            #~ numlinechars=self.options['numlinechars'],
            #~ usemonospacedfont=self.options['usemonospacedfont'],
            #~ textstyles=self.options['textstyles'],
        )
        # Bind variables to the window instance
        scriptWindow.filename = ""
        scriptWindow.AVI = None
        scriptWindow.previewtxt = []
        scriptWindow.sliderTexts = []
        scriptWindow.sliderProperties = []
        scriptWindow.toggleTags = []
        scriptWindow.autoSliderInfo = []
        scriptWindow.lastSplitVideoPos = None
        scriptWindow.lastSplitSliderPos = -300
        scriptWindow.userHidSliders = False
        scriptWindow.lastFramenum = 0
        scriptWindow.sliderWindowShown = not self.options['keepsliderwindowhidden']
        try:
            #scriptWindow.contextMenu = self.GetMenuBar().GetMenu(1)
            scriptWindow.contextMenu = self.menuBackups[0] if self.menuBackups else self.GetMenuBar().GetMenu(1)
        except AttributeError:
            pass

        scriptWindow.sliderWindow = wx.ScrolledWindow(self.videoSplitter, wx.ID_ANY, style=wx.STATIC_BORDER|wx.TAB_TRAVERSAL)
        scriptWindow.sliderWindow.SetScrollRate(10, 10)
        scriptWindow.sliderSizer = wx.GridBagSizer(hgap=0, vgap=10)
        if wx.VERSION < (2, 9):
            scriptWindow.sliderSizer.AddGrowableCol(3)
        #~ scriptWindow.sliderSizerNew = wx.GridBagSizer(hgap=0, vgap=10)
        scriptWindow.sliderSizerNew = wx.GridBagSizer(hgap=0, vgap=0)
        if wx.VERSION < (2, 9):
            scriptWindow.sliderSizerNew.AddGrowableCol(3)
        scriptWindow.sliderSizerNew.SetEmptyCellSize((0,0)) 
        scriptWindow.toggleTagSizer = wx.BoxSizer(wx.VERTICAL)
        scriptWindow.videoSidebarSizer = wx.BoxSizer(wx.VERTICAL)
        scriptWindow.videoSidebarSizer.Add(scriptWindow.toggleTagSizer, 0, wx.TOP|wx.LEFT, 5)
        scriptWindow.videoSidebarSizer.Add(scriptWindow.sliderSizerNew, 0, wx.EXPAND|wx.LEFT, 5)
        scriptWindow.videoSidebarSizer.Add(scriptWindow.sliderSizer, 0, wx.EXPAND|wx.LEFT, 5)
        scriptWindow.sliderWindow.SetSizer(scriptWindow.videoSidebarSizer)
        scriptWindow.sliderWindow.Bind(wx.EVT_LEFT_DOWN, lambda event: self.videoWindow.SetFocus())
        scriptWindow.oldSliderTexts = []
        scriptWindow.oldAutoSliderInfo = []
        scriptWindow.oldToggleTags = []
        scriptWindow.zoomwindow_actualsize = None
        #~ scriptWindow.lastSplitVideoPos = None

        # Event binding
        scriptWindow.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)
        scriptWindow.Bind(wx.EVT_MIDDLE_DOWN, self.OnMiddleDownScriptWindow)
        scriptWindow.Bind(wx.EVT_MIDDLE_UP, self.OnMiddleUpScriptWindow)
        scriptWindow.Bind(wx.EVT_SET_FOCUS, self.OnFocusScriptWindow)
        scriptWindow.Bind(stc.EVT_STC_UPDATEUI, self.OnScriptTextChange)
        #~ scriptWindow.Bind(stc.EVT_STC_SAVEPOINTLEFT, self.OnScriptSavePointLeft)
        #~ scriptWindow.Bind(stc.EVT_STC_SAVEPOINTREACHED, self.OnScriptSavePointReached)
        scriptWindow.Bind(stc.EVT_STC_SAVEPOINTLEFT, lambda event: self.SetScriptTabname(event.GetEventObject()))
        scriptWindow.Bind(stc.EVT_STC_SAVEPOINTREACHED, lambda event: self.SetScriptTabname(event.GetEventObject()))
        scriptWindow.Bind(wx.EVT_KEY_UP, self.OnScriptKeyUp)
        # Drag-and-drop target
        scriptWindow.SetDropTarget(self.scriptDropTarget(scriptWindow, self))
        return scriptWindow

    def createVideoWindow(self, parent):
        videoWindow = wx.ScrolledWindow(parent, style=wx.STATIC_BORDER|wx.WANTS_CHARS)
        videoWindow.SetScrollRate(1, 1)
        try:
            #videoWindow.contextMenu = self.GetMenuBar().GetMenu(2)
            videoWindow.contextMenu = self.menuBackups[1] if self.menuBackups else self.GetMenuBar().GetMenu(2)
        except AttributeError:
            pass
        # Event binding
        videoWindow.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)
        videoWindow.Bind(wx.EVT_SET_FOCUS, self.OnFocusVideoWindow)
        videoWindow.Bind(wx.EVT_PAINT, self.OnPaintVideoWindow)
        videoWindow.Bind(wx.EVT_KEY_DOWN, self.OnKeyDownVideoWindow)
        videoWindow.Bind(wx.EVT_MOUSEWHEEL, self.OnMouseWheelVideoWindow)
        videoWindow.Bind(wx.EVT_MIDDLE_DOWN, self.OnMiddleDownVideoWindow)
        videoWindow.Bind(wx.EVT_LEFT_DOWN, self.OnLeftDownVideoWindow)
        videoWindow.Bind(wx.EVT_MOTION, self.OnMouseMotionVideoWindow)
        videoWindow.Bind(wx.EVT_LEAVE_WINDOW, self.OnMouseLeaveVideoWindow)
        videoWindow.Bind(wx.EVT_LEFT_UP, self.OnLeftUpVideoWindow)
        return videoWindow

    def createVideoControls(self, parent, primary=True):
        if wx.VERSION < (2, 9):
            panel = wx.Panel(parent, style=wx.BORDER_NONE, size=(-1, 24))
        else:
            panel = wx.Panel(parent, size=(-1, 30))
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        videoControlWidgets = []
        # Create the playback buttons
        for bitmap, handler, statusTxt in self.buttonInfo():
            button = self.createToolbarButton(panel, bitmap, handler, statusTxt=statusTxt)
            if handler == self.OnMenuVideoToggle:
                if primary:
                    self.toggleButton = button
                else:
                    self.toggleButton2 = button
                    self.toggleButton2.SetBitmapLabel(self.bmpVidDown)
            sizer.Add(button, 0, wx.ALIGN_CENTER_VERTICAL)#, wx.EXPAND)#, wx.ALIGN_BOTTOM)#, wx.ALL, 1)
            videoControlWidgets.append(button)
        # Create the frame textbox
        frameTextCtrl = wx.TextCtrl(panel, wx.ID_ANY, size=(80,-1), style=wx.TE_RIGHT|wx.TE_PROCESS_ENTER)
        frameTextCtrl.Bind(wx.EVT_TEXT_ENTER, self.OnButtonTextKillFocus)
        frameTextCtrl.Bind(wx.EVT_KILL_FOCUS, self.OnButtonTextKillFocus)
        frameTextCtrl.Bind(wx.EVT_SET_FOCUS, self.OnButtonTextSetFocus)        
        frameTextCtrl.Bind(wx.EVT_CONTEXT_MENU, self.OnButtonTextContextMenu)
        frameTextCtrl.Replace(0, -1, str(0))
        if wx.VERSION < (2, 9):
            sizer.Add(frameTextCtrl, 0, wx.TOP|wx.LEFT, 4)
        else:
            sizer.Add(frameTextCtrl, 0, wx.ALIGN_CENTRE_VERTICAL|wx.LEFT, 4)
        videoControlWidgets.append(frameTextCtrl)
        if primary:
            self.frameTextCtrl = frameTextCtrl
        else:
            self.frameTextCtrl2 = frameTextCtrl
        # Create the video slider
        if primary:
            #~ self.videoSlider = wxp.Slider(panel, wx.ID_ANY, 0, 0, 240-1, style=wx.SL_HORIZONTAL|wx.SL_SELRANGE|wx.SL_AUTOTICKS, onscroll=self.OnSliderChanged)
            #~ self.videoSlider = wxp.Slider(panel, wx.ID_ANY, 0, 0, 240-1, style=wx.SL_HORIZONTAL|wx.SL_SELRANGE, onscroll=self.OnSliderChanged)
            self.videoSlider = SliderPlus(panel, wx.ID_ANY, 0, 0, 240-1, bookmarkDict=self.bookmarkDict)
            self.videoSlider.Bind(wx.EVT_SCROLL_THUMBTRACK, self.OnSliderChanged)
            self.videoSlider.Bind(wx.EVT_SCROLL_ENDSCROLL, self.OnSliderReleased)
            self.videoSlider.Bind(wx.EVT_RIGHT_UP, self.OnSliderRightUp)
            self.videoSlider.Bind(wx.EVT_MIDDLE_DOWN, self.OnSliderMiddleDown)
            self.videoSlider.Bind(wx.EVT_LEFT_UP, self.OnSliderLeftUp)
            sizer.Add(self.videoSlider, 1, wx.EXPAND)
            videoControlWidgets.append(self.videoSlider)
        else:
            #~ self.videoSlider = wxp.Slider(panel, wx.ID_ANY, 0, 0, 240-1, style=wx.SL_HORIZONTAL|wx.SL_SELRANGE|wx.SL_AUTOTICKS, onscroll=self.OnSliderChanged)
            #~ self.videoSlider2 = wxp.Slider(panel, wx.ID_ANY, 0, 0, 240-1, style=wx.SL_HORIZONTAL|wx.SL_SELRANGE, onscroll=self.OnSliderChanged)
            #~ self.videoSlider.Bind(wx.EVT_SCROLL, self.OnSliderChanged)
            self.videoSlider2 = SliderPlus(panel, wx.ID_ANY, 0, 0, 240-1, bookmarkDict=self.bookmarkDict)
            self.videoSlider2.Bind(wx.EVT_SCROLL_THUMBTRACK, self.OnSliderChanged)
            self.videoSlider2.Bind(wx.EVT_SCROLL_ENDSCROLL, self.OnSliderReleased)
            self.videoSlider2.Bind(wx.EVT_RIGHT_UP, self.OnSliderRightUp)
            self.videoSlider2.Bind(wx.EVT_MIDDLE_DOWN, self.OnSliderMiddleDown)
            self.videoSlider2.Bind(wx.EVT_LEFT_UP, self.OnSliderLeftUp)
            sizer.Add(self.videoSlider2, 1, wx.EXPAND)
            videoControlWidgets.append(self.videoSlider2)

        if primary:
            self.videoControlWidgets = videoControlWidgets
        else:
            self.videoControlWidgets2 = videoControlWidgets

        if self.options['disablepreview'] and primary:
            for ctrl in self.videoControlWidgets:
                ctrl.Disable()
                ctrl.Refresh()
        # Set the sizer and return the panel
        panel.SetSizer(sizer)
        return panel

    def createCropDialog(self, parent):
        dlg = wx.Dialog(parent, wx.ID_ANY, _('Crop editor'),
                        style=wx.DEFAULT_DIALOG_STYLE|wx.STAY_ON_TOP)
        dlg.ctrls = {}
        # Create the crop spin controls
        spinSizer = wx.GridBagSizer(hgap=5, vgap=5)
        spinInfo = (
            ('left', (1,0), (1,1)),
            ('top', (0,2), (0,3)),
            ('-right', (1,4), (1,5)),
            ('-bottom', (2,2), (2,3)),
        )
        for name, txtPos, spinPos in spinInfo:
            staticText = wx.StaticText(dlg, wx.ID_ANY, name)
            spinCtrl = wx.SpinCtrl(dlg, wx.ID_ANY, '', size=(50,-1))
            spinCtrl.Bind(wx.EVT_TEXT, self.OnCropDialogSpinTextChange)
            spinSizer.Add(staticText, txtPos, flag=wx.ALIGN_CENTER|wx.RIGHT, border=5)
            spinSizer.Add(spinCtrl, spinPos, flag=wx.EXPAND|wx.RIGHT, border=0)
            dlg.ctrls[name] = spinCtrl
            dlg.ctrls[name+'Label'] = staticText
        # Create a static text message
        staticText = wx.StaticText(dlg, wx.ID_ANY,
            _(
                'You can drag the crop regions with the left mouse button when '
                'this dialog is visible, cropping the edge closest to the '
                'initial mouse click.'
            )
        )
        staticText.Wrap(spinSizer.GetMinSize()[0])
        # Create the choice box for insertion options
        choiceBox = wx.Choice(
            dlg, wx.ID_ANY,
            choices=(
                _('At script end'),
                _('At script cursor'),
                _('Copy to clipboard')
            )
        )
        choiceBox.SetSelection(self.options['cropchoice'])
        choiceLabel = wx.StaticText(dlg, wx.ID_ANY, _('Insert Crop() command:'))
        choiceSizer = wx.BoxSizer(wx.HORIZONTAL)
        choiceSizer.Add(choiceLabel, 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 5)
        choiceSizer.Add(choiceBox, 1, wx.EXPAND|wx.LEFT, 5)
        dlg.ctrls['choiceInsert'] = choiceBox
        # Create the dialog buttons
        buttonApply = wx.Button(dlg, wx.ID_OK, _('Apply'))
        dlg.Bind(wx.EVT_BUTTON, self.OnCropDialogApply, buttonApply)
        buttonCancel = wx.Button(dlg, wx.ID_CANCEL, _('Cancel'))
        dlg.Bind(wx.EVT_BUTTON, self.OnCropDialogCancel, buttonCancel)
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(buttonApply, 0, wx.ALL, 5)
        buttonSizer.Add(buttonCancel, 0, wx.ALL, 5)
        # Size the elements
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(spinSizer, 0, wx.ALL, 10)
        sizer.Add(choiceSizer, 0, wx.TOP|wx.BOTTOM, 10)
        sizer.Add(wx.StaticLine(dlg), 0, wx.EXPAND)
        sizer.Add(staticText, 0, wx.ALIGN_CENTER|wx.EXPAND|wx.ALL, 5)
        sizer.Add(buttonSizer, 0, wx.ALIGN_CENTER|wx.ALL, 10)
        dlg.SetSizer(sizer)
        dlg.Fit()
        # Events
        dlg.Bind(wx.EVT_CLOSE, self.OnCropDialogCancel)
        buttonApply.SetDefault()
        return dlg

    def createTrimDialog(self, parent):
        dlg = wx.Dialog(parent, wx.ID_ANY, _('Trim editor'),
                        style=wx.DEFAULT_DIALOG_STYLE|wx.STAY_ON_TOP)
        dlg.ctrls = {}
        # Create the radio box for Crop() options
        radioBoxTrim = wx.RadioBox(
            dlg, wx.ID_ANY, _('Selection options'),
            choices=(
                _('Keep selected regions'),
                _('Keep unselected regions')
            ),
            majorDimension=2,
            style=wx.RA_SPECIFY_ROWS,
        )
        def OnRadioBoxTrim(event):
            if event.GetSelection() == 0:
                self.invertSelection = False
            else:
                self.invertSelection = True
            self.ShowVideoFrame()
            event.Skip()
        radioBoxTrim.Bind(wx.EVT_RADIOBOX, OnRadioBoxTrim)
        radioBoxTrim.SetSelection(self.options['trimreversechoice'])
        dlg.ctrls['radioTrim'] = radioBoxTrim
        # Create the checkbox for marking frames
        checkBox = wx.CheckBox(dlg, wx.ID_ANY, _('Mark video frames inside/outside selection'))
        def OnCheckBox(event):
            self.markFrameInOut = event.IsChecked()
            self.ShowVideoFrame()
            event.Skip()
        checkBox.Bind(wx.EVT_CHECKBOX, OnCheckBox)
        checkBox.SetValue(self.options['trimmarkframes'])
        # Create a checkbox and a spinctrl for using Dissolve()
        checkBox2 = wx.CheckBox(dlg, wx.ID_ANY, _('Use Dissolve() with overlap frames:'))
        def OnCheckBox2(event):
            if event.IsChecked():
                spinCtrl.Enable(True)
                choiceLabel.SetLabel(dissolveTxt)
            else:
                spinCtrl.Enable(False)
                choiceLabel.SetLabel(trimTxt)
        checkBox2.Bind(wx.EVT_CHECKBOX, OnCheckBox2)
        dlg.ctrls['useDissolve'] = checkBox2
        spinCtrl = wx.SpinCtrl(dlg, wx.ID_ANY, size=(50, -1), max=999)
        spinCtrl.Enable(False)
        if wx.VERSION < (2, 8):
            spinCtrl.SetValue(0)
            spinCtrl.Bind(wx.EVT_TEXT, self.OnTrimDialogSpinTextChange)
        dlg.ctrls['dissolveOverlap'] = spinCtrl
        dissolveSizer = wx.BoxSizer(wx.HORIZONTAL)
        dissolveSizer.Add(checkBox2, 0, wx.TOP, 3)
        dissolveSizer.Add(spinCtrl)
        # Create the choice box for insertion options
        choiceBoxInsert = wx.Choice(
            dlg, wx.ID_ANY,
            choices=(
                _('At script end'),
                _('At script cursor'),
                _('Copy to clipboard')
            )
        )
        choiceBoxInsert.SetSelection(self.options['triminsertchoice'])
        trimTxt = _('Insert Trim() commands:')
        dissolveTxt = _('Insert Dissolve() commands:')
        labelSize = self.GetTextExtent(dissolveTxt)
        choiceLabel = wx.StaticText(dlg, wx.ID_ANY, _('Insert Trim() commands:'),
                                    size=labelSize, style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE)
        choiceSizer = wx.BoxSizer(wx.HORIZONTAL)
        choiceSizer.Add(choiceLabel, 0, wx.ALIGN_CENTER_VERTICAL)
        choiceSizer.Add(choiceBoxInsert, 0, wx.RIGHT, 5)
        dlg.ctrls['choiceInsert'] = choiceBoxInsert
        # Create a static text message
        staticText = wx.StaticText(dlg, wx.ID_ANY,
            _(
                'Use the buttons which appear on the video slider '
                'handle to create the frame selections to trim.'
            )
        )
        staticText.Wrap(choiceSizer.GetMinSize()[0])
        # Create the dialog buttons
        buttonApply = wx.Button(dlg, wx.ID_OK, _('Apply'))
        dlg.Bind(wx.EVT_BUTTON, self.OnTrimDialogApply, buttonApply)
        buttonCancel = wx.Button(dlg, wx.ID_CANCEL, _('Cancel'))
        dlg.Bind(wx.EVT_BUTTON, self.OnTrimDialogCancel, buttonCancel)
        buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        buttonSizer.Add(buttonApply, 0, wx.ALL, 5)
        buttonSizer.Add(buttonCancel, 0, wx.ALL, 5)
        # Size the elements
        sizer = wx.BoxSizer(wx.VERTICAL)
        #~ sizer.Add(spinSizer, 0, wx.ALL, 10)
        sizer.Add(radioBoxTrim, 0, wx.EXPAND|wx.ALIGN_CENTER|wx.ALL, 5)
        sizer.Add(checkBox, 0, wx.ALL, 10)
        sizer.Add(dissolveSizer, 0, wx.LEFT|wx.RIGHT|wx.BOTTOM, 10)
        sizer.Add(choiceSizer, 0, wx.ALL, 5)
        sizer.Add(wx.StaticLine(dlg), 0, wx.EXPAND|wx.TOP, 5)
        sizer.Add(staticText, 0, wx.ALIGN_CENTER|wx.EXPAND|wx.ALL, 5)
        sizer.Add(buttonSizer, 0, wx.ALIGN_CENTER|wx.ALL, 10)
        dlg.SetSizer(sizer)
        dlg.Fit()
        # Events
        dlg.Bind(wx.EVT_CLOSE, self.OnTrimDialogCancel)
        buttonApply.SetDefault()
        return dlg

    # Event functions
    def OnClose(self, event):
        self.ExitProgram()

    def OnMenuFileNew(self, event):
        self.NewTab()

    def OnMenuFileOpen(self, event):
        self.OpenFile()

    def OnMenuFileClose(self, event):
        self.CloseTab(boolPrompt=True)

    def OnMenuFileCloseAllTabs(self, event):
        self.CloseAllTabs()

    def OnMenuFileSaveScript(self, event):
        index = self.scriptNotebook.GetSelection()
        script = self.scriptNotebook.GetPage(index)
        self.SaveScript(script.filename, index)

    def OnMenuFileSaveScriptAs(self, event):
        self.SaveScript()
        
    def OnMenuFileRenameTab(self, index, pos=None):
        if not self.scriptNotebook.dblClicked\
        and not self.titleEntry\
        and not self.scriptNotebook.HasCapture()\
        and not (pos and index != self.scriptNotebook.GetSelection()):
            if pos == None:
                index = self.scriptNotebook.GetSelection()
                h = self.scriptNotebook.GetCharHeight() + 6
                for row in range(self.scriptNotebook.GetRowCount()):
                    y = h * row + h/2
                    for x in range(0, self.scriptNotebook.GetSizeTuple()[0], h):
                        ipage = self.scriptNotebook.HitTest((x, y))[0]
                        if ipage == index:
                            pos = (x, y)
                            break
                    if pos:
                        break
            if pos == None:
                return
            x, y = pos
            ipage = index
            while ipage == index:
                x -= 1
                ipage = self.scriptNotebook.HitTest((x, y))[0]
            left = x + 1
            x, y = pos
            ipage = index
            while ipage == index:
                y -= 1
                ipage = self.scriptNotebook.HitTest((x, y))[0]
            top = y + 1
            x, y = pos
            ipage = index
            while ipage == index:
                x += 1
                ipage = self.scriptNotebook.HitTest((x, y))[0]
            right = x - 1
            x, y = pos
            ipage = index
            while ipage == index:
                y += 1
                ipage = self.scriptNotebook.HitTest((x, y))[0]
            bottom = y - 1
            title = self.scriptNotebook.GetPageText(index)
            if title.startswith('* '):
                title = title.lstrip('* ')
                unsaved = '* '
            else:
                unsaved = ''
            self.titleEntry = wx.TextCtrl(self.scriptNotebook, -1, title, pos=(left, top), size=(right-left, bottom-top), style=wx.TE_PROCESS_ENTER|wx.BORDER_SIMPLE)
            self.titleEntry.SetFocus()
            self.titleEntry.SetSelection(-1, -1)
            
            def OnTabKillFocus(event):
                if self.FindFocus() == self.scriptNotebook:
                    if self.scriptNotebook.GetPageImage(index) == -1:
                        self.currentScript.SetFocus()
                    else:
                        self.videoWindow.SetFocus()
                title = self.titleEntry.GetLineText(0)
                if self.currentScript.filename:
                    if not title.endswith('.avs') and not title.endswith('.avsi'):
                        title += '.avs'
                    src = self.currentScript.filename
                    dirname = os.path.dirname(src)
                    dst = os.path.join(dirname, title)
                    try:
                        os.rename(src, dst)
                        self.currentScript.filename = dst
                    except OSError:
                        wx.Bell()
                        self.IdleCall.append((self.titleEntry.Destroy, tuple(), {}))
                        return
                self.scriptNotebook.SetPageText(index, unsaved + title)
                self.IdleCall.append((self.titleEntry.Destroy, tuple(), {}))
                
            def CheckTabPosition():
                try:
                    if self.titleEntry:
                        if self.scriptNotebook.HitTest((left, top))[0] != index\
                        or self.scriptNotebook.HitTest((right, bottom))[0] != index:
                            self.scriptNotebook.SetFocus()
                        else:
                            wx.CallLater(300, CheckTabPosition)
                except wx.PyDeadObjectError:
                    pass
                
            self.titleEntry.Bind(wx.EVT_KILL_FOCUS, OnTabKillFocus)
            self.titleEntry.Bind(wx.EVT_TEXT_ENTER, OnTabKillFocus)
            wx.CallLater(300, CheckTabPosition)
        if self.scriptNotebook.dblClicked:
            wx.CallLater(300, setattr, self.scriptNotebook, 'dblClicked' ,False)        

    def OnMenuFileLoadSession(self, event):
        self.LoadSession()
        self.SaveSession(self.lastSessionFilename, saverecentdir=False, previewvisible=False)
        
    def OnMenuFileSaveSession(self, event):
        self.SaveSession()

    def OnMenuFileBackupSession(self, event):
        self.SaveSession(self.lastSessionFilename, saverecentdir=False, previewvisible=False)

    def _x_OnMenuFileExportFilters(self, event):
        self.ShowFunctionExportImportDialog(export=True)

    def _x_OnMenuFileImportFilters(self, event):
        self.ShowFunctionExportImportDialog(export=False)

    def OnMenuFileNextTab(self, event):
        self.SelectTab(inc=1)

    def OnMenuFilePrevTab(self, event):
        self.SelectTab(inc=-1)

    def OnMenuFileRecentFile(self, event):
        # First find the position of the clicked menu item
        id = event.GetId()
        menuItem = self.GetMenuBar().FindItemById(id)
        menu = menuItem.GetMenu()
        nMenuItems = menu.GetMenuItemCount()
        pos = None
        for i in xrange(nMenuItems):
            if menu.FindItemByPosition(i).GetId() == id:
                pos = i
                break
        if pos is None:
            return
        # Find the menu position of the first filename
        firstpos = None
        i = nMenuItems - 1 - 2
        while i >= 0:
            menuItem = menu.FindItemByPosition(i)
            if menuItem.IsSeparator():
                firstpos = i + 1
                break
            i -= 1
        if firstpos is None:
            return
        # Compute the relative position
        relpos = pos - firstpos
        # Open the corresponding filename
        try:
            filename = self.options['recentfiles'][relpos]
            if os.path.isfile(filename):
                self.OpenFile(filename)
            else:
                wx.MessageBox(_('File does not exist!'), _('Error'), style=wx.OK|wx.ICON_ERROR)
        except IndexError:
            pass

    def OnMenuFileExit(self, event):
        self.ExitProgram()

    def OnMenuEditUndo(self, event):
        script = self.currentScript
        script.Undo()

    def OnMenuEditRedo(self, event):
        script = self.currentScript
        script.Redo()

    def OnMenuEditCut(self, event):
        script = self.currentScript
        script.Cut()

    def OnMenuEditCopy(self, event):
        script = self.currentScript
        script.Copy()

    def OnMenuEditPaste(self, event):
        script = self.currentScript
        script.Paste()

    def OnMenuEditFind(self, event):
        script = self.currentScript
        script.ShowFindDialog()

    def OnMenuEditFindNext(self, event):
        script = self.currentScript
        script.FindNext()

    def OnMenuEditReplace(self, event):
        script = self.currentScript
        script.ShowReplaceDialog()

    def OnMenuEditSelectAll(self, event):
        script = self.currentScript
        script.SelectAll()

    def OnMenuEditInsertSource(self, event):
        self.InsertSource()

    def OnMenuEditInsertFilename(self, event):
        filefilter = _('All files (*.*)|*.*')
        recentdir =  self.options['recentdir']
        dlg = wx.FileDialog(self, _('Select a file'), recentdir, '', filefilter, wx.OPEN)
        ID = dlg.ShowModal()
        if ID == wx.ID_OK:
            filename = dlg.GetPath()
            self.InsertText(filename, pos=None)
            dirname = os.path.dirname(filename)
            if os.path.isdir(dirname):
                self.options['recentdir'] = dirname
        dlg.Destroy()

    def OnMenuEditInsertPlugin(self, event):
        self.InsertPlugin()

    def OnMenuEditInsertFrameNumber(self, event):
        self.InsertFrameNumber()

    def OnMenuEditInsertUserSlider(self, event):
        self.InsertUserSlider()

    def OnMenuEditInsertUserSliderSeparator(self, event):
        script = self.currentScript
        dlg = wx.TextEntryDialog(self, _('Enter separator label'), _('Create a separator label'))
        ID = dlg.ShowModal()
        if ID == wx.ID_OK:
            label = dlg.GetValue()
            if label != '':
                script.ReplaceSelection('[<separator="%s">]' % label.replace(',', '_'))
            else:
                script.ReplaceSelection('[<separator>]')
        dlg.Destroy()

    def _x_OnMenuEditInsertBookmarkTrims(self, event):
        self.InsertBookmarkTrims()

    def _x_OnMenuEditInsertTrimSelectedOut(self, event):
        self.InsertSelectionTrims(cutSelected=True)

    def _x_OnMenuEditInsertTrimUnSelectedOut(self, event):
        self.InsertSelectionTrims(cutSelected=False)

    def OnMenuEditToggleTagSelection(self, event):
        script = self.currentScript
        # Get the name of the tag
        label = None
        dlg = wx.TextEntryDialog(self, _('Enter tag name:'), _('Tag definition'), '')
        if dlg.ShowModal() == wx.ID_OK:
            label = dlg.GetValue()
        dlg.Destroy()
        # Insert the tags into the text
        if label is not None:
            startpos, endpos = script.GetSelection()
            startline = script.LineFromPosition(startpos)
            endline = script.LineFromPosition(endpos)
            firstpos = script.PositionFromLine(startline)
            lastpos = script.GetLineEndPosition(endline)
            lastfirstpos = script.PositionFromLine(endline)
            extraA = extraB = ''
            extraAA = extraBB = ''
            if startpos == firstpos and (endpos == lastpos or endpos == lastfirstpos):
                extraA = '\n'
                if endpos == lastpos:
                    extraB = '\n'
                if endpos == lastfirstpos:
                    extraBB = '\n'
            script.InsertText(endpos, '%s[/%s]%s' % (extraB, label, extraBB))
            script.InsertText(startpos, '%s[%s]%s' % (extraAA, label, extraA))

    def OnMenuEditClearToggleTags(self, event):
        script = self.currentScript
        script.SetText(self.cleanToggleTags(script.GetText()))

    def OnMenuEditIndentSelection(self, event=None):
        self.currentScript.CmdKeyExecute(stc.STC_CMD_TAB)
        #~ script = self.currentScript
        #~ lineA = script.LineFromPosition(script.GetSelectionStart())
        #~ lineB = script.LineFromPosition(script.GetSelectionEnd())
        #~ if lineA==lineB:
            #~ script.GotoLine(lineA)
            #~ posA = script.GetCurrentPos()
            #~ script.CmdKeyExecute(stc.STC_CMD_TAB)
            #~ posB = script.GetLineEndPosition(lineA)
            #~ script.SetSelection(posB,posA)
        #~ else:
            #~ script.CmdKeyExecute(stc.STC_CMD_TAB)
        #~ if self.tab_processed:
            #~ self.tab_processed = False
        #~ else:
            #~ script.CmdKeyExecute(stc.STC_CMD_TAB)

    def OnMenuEditUnIndentSelection(self, event):
        script = self.currentScript
        lineA = script.LineFromPosition(script.GetSelectionStart())
        lineB = script.LineFromPosition(script.GetSelectionEnd())
        if lineA==lineB:
            script.GotoLine(lineA)
            posA = script.GetCurrentPos()
            script.CmdKeyExecute(stc.STC_CMD_BACKTAB)
            posB = script.GetLineEndPosition(lineA)
            script.SetSelection(posB,posA)
        else:
            script.CmdKeyExecute(stc.STC_CMD_BACKTAB)

    def OnMenuEditBlockComment(self, event):
        script = self.currentScript
        script.BlockComment()
    
    def OnMenuEditStyleComment(self, event):
        script = self.currentScript
        script.StyleComment()
    
    def OnMenuEditToggleCurrentFold(self, event):
        script = self.currentScript
        script.ToggleFold(script.GetCurrentLine())
        
    def OnMenuEditToggleAllFolds(self, event):
        script = self.currentScript
        script.FoldAll()

    def OnMenuEditMoveLineUp(self, event):
        self.currentScript.MoveSelectionByOneLine(up=True)
        self.AutoUpdateVideo(force=True)

    def OnMenuEditMoveLineDown(self, event):
        self.currentScript.MoveSelectionByOneLine(up=False)
        self.AutoUpdateVideo(force=True)

    def OnMenuEditAutocomplete(self, event):
        if self.currentScript.AutoCompActive():
            self.currentScript.CmdKeyExecute(wx.stc.STC_CMD_CANCEL)
        else:
            self.currentScript.ShowAutocomplete()
        
    def OnMenuEditAutocompleteAll(self, event):
        if self.currentScript.AutoCompActive():
            self.currentScript.CmdKeyExecute(wx.stc.STC_CMD_CANCEL)
        else:
            self.currentScript.ShowAutocomplete(all=True)
        
    def OnMenuEditShowCalltip(self, event):
        if self.currentScript.CallTipActive():
            self.currentScript.CmdKeyExecute(wx.stc.STC_CMD_CANCEL)
        else:
            self.currentScript.UpdateCalltip(force=True)

    def OnMenuEditShowFunctionDefinition(self, event):
        name = self.currentScript.GetFilterNameAtCursor()
        self.ShowFunctionDefinitionDialog(functionName=name)

    def OnMenuEditFilterHelp(self, event):
        script = self.currentScript
        if script.calltipFilter is not None:
            script.ShowFilterDocumentation()
        else:
            pos = script.GetCurrentPos()
            posA = script.WordStartPosition(pos, 1)
            posB = script.WordEndPosition(pos, 1)
            word = script.GetTextRange(posA, posB)
            #~ if word.lower() in script.keywords:
            if word.lower() in self.avskeywords:
                script.ShowFilterDocumentation(word)
            else:
                script.ShowFilterDocumentation(script.GetSelectedText())

    def OnMenuEditCopyToNewTab(self, event):
        self.CopyTextToNewTab()

    def OnMenuCopyUnmarkedScript(self, event):
        txt = self.getCleanText(self.currentScript.GetText()).replace('\n', '\r\n')
        text_data = wx.TextDataObject(txt)
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(text_data)
            wx.TheClipboard.Close()

    def OnMenuCopyAvisynthError(self, event):
        if self.currentScript.AVI and self.currentScript.AVI.error_message and not wx.TheClipboard.IsOpened():            
            text_data = wx.TextDataObject(self.currentScript.AVI.error_message)
            wx.TheClipboard.Open()
            wx.TheClipboard.SetData(text_data)
            wx.TheClipboard.Close()
            
    def OnMenuCopyStatusBar(self, event):
        if not wx.TheClipboard.IsOpened():
            statusBar = self.GetStatusBar()
            text = ' '.join(statusBar.GetFields())
            text_data = wx.TextDataObject(text)
            wx.TheClipboard.Open()
            wx.TheClipboard.SetData(text_data)
            wx.TheClipboard.Close()
            
    def OnMenuEditShowScrapWindow(self, event):
        scrap = self.scrapWindow
        if scrap.IsShown():
            scrap.Hide()
        else:
            scrap.Show()

    def OnMenuVideoBookmark(self, event):
        framenum = self.GetFrameNumber()
        self.AddFrameBookmark(framenum)

    def _x_OnMenuVideoBookmarkStart(self, event):
        framenum = self.GetFrameNumber()
        self.AddFrameBookmark(framenum, bmtype=1, toggle=False)

    def _x_OnMenuVideoBookmarkEnd(self, event):
        framenum = self.GetFrameNumber()
        self.AddFrameBookmark(framenum, bmtype=2, toggle=False)

    def OnMenuVideoGotoFrameNumber(self, event):
        #~ bmenu = self.GetMenuBar().GetMenu(2).FindItemByPosition(1).GetSubMenu()
        #~ framenum = int(bmenu.GetLabel(event.GetId()))
        menuItem = self.GetMenuBar().FindItemById(event.GetId())
        framenum = int(menuItem.GetLabel().split()[0])
        self.ShowVideoFrame(framenum)

    def OnMenuVideoBookmarkMoveTitle(self, event):
        if type(event) is int:
            curr = event
        else:
            curr = self.GetFrameNumber()
        bookmarkList = [bookmark for bookmark, bmtype in self.GetBookmarkFrameList() if bmtype == 0]
        diffList = [(abs(curr - i), i) for i in self.bookmarkDict if self.bookmarkDict[i]]
        if not diffList:
            return
        diff, bookmark = min(diffList)
        if bookmark not in bookmarkList:
            self.AddFrameBookmark(bookmark)
            return
        if not diff: 
            return
        self.bookmarkDict[curr] = self.bookmarkDict[bookmark]
        del self.bookmarkDict[bookmark]
        if curr not in bookmarkList:
            self.AddFrameBookmark(curr, refreshProgram=False)
        self.DeleteFrameBookmark(bookmark)
            
    def OnMenuVideoBookmarkRestoreHistory(self, event):
        bookmarkList = [bookmark for bookmark, bmtype in self.GetBookmarkFrameList() if bmtype == 0]
        for bookmark in self.bookmarkDict.keys():
            if bookmark not in bookmarkList and self.bookmarkDict[bookmark]:
                self.OnMenuVideoBookmarkMoveTitle(bookmark)

    def OnMenuVideoBookmarkClearHistory(self, event):
        bookmarkList = [bookmark for bookmark, bmtype in self.GetBookmarkFrameList() if bmtype == 0]
        for bookmark in self.bookmarkDict.keys():
            if bookmark not in bookmarkList or not self.bookmarkDict[bookmark]:
                del self.bookmarkDict[bookmark]
                
    def OnMenuVideoBookmarkAutoTitle(self, event):
        bookmarkList = [bookmark for bookmark, bmtype in self.GetBookmarkFrameList() if bmtype == 0]
        bookmarkList.sort()
        for i in range(len(bookmarkList)):
            if bookmarkList[i] not in self.bookmarkDict:
                self.bookmarkDict[bookmarkList[i]] = _('Chapter') + (' %02d' % (i+1))
        self.UpdateBookmarkMenu()
        if self.previewWindowVisible:
            self.videoSlider.Refresh()
            if self.separatevideowindow:
                self.videoSlider2.Refresh()
        
    def OnMenuVideoBookmarkSetTitle(self, event):
        bookmarkInfo = []
        historyList = []
        titleList = []
        bookmarkList = [bookmark for bookmark, bmtype in self.GetBookmarkFrameList() if bmtype == 0]
        for bookmark in self.bookmarkDict:
            if bookmark in bookmarkList:
                titleList.append(bookmark)
            else:
                historyList.append(bookmark)                
        bookmarkList += historyList
        if not bookmarkList:
            return
        for bookmark in bookmarkList:
            if self.currentScript.AVI:
                sec = bookmark / self.currentScript.AVI.Framerate                    
                min, sec = divmod(sec, 60)
                hr, min = divmod(min, 60)
                timecode = '%02d:%02d:%06.3f' % (hr, min, sec)
            else:
                timecode = '??:??:??.???'
            title = self.bookmarkDict.get(bookmark, '')
            bookmarkInfo.append((bookmark, timecode, title))
        bookmarkInfo.sort()
        dlg = wx.Dialog(self, wx.ID_ANY, _('Set title for bookmarks'), size=(450, 270), style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        attrTitle = wx.ListItemAttr()
        attrTitle.SetTextColour(wx.BLUE)
        attrHistory = wx.ListItemAttr()
        attrHistory.SetTextColour(wx.RED)
        # Define the virtual list control
        class VListCtrl(wxp.ListCtrl):                
            def OnGetItemText(self, item, column):
                bookmark, timecode, title = bookmarkInfo[item]
                if column == 0:
                    return title
                elif column == 1:
                    if bookmark in historyList:
                        return '* ' + str(bookmark)
                    return str(bookmark)
                return timecode
                
            def OnGetItemAttr(self, item):
                bookmark, timecode, title = bookmarkInfo[item]
                if bookmark in titleList:
                    return attrTitle
                elif bookmark in historyList:
                    return attrHistory
                    
        listCtrl = VListCtrl(dlg, wx.ID_ANY, style=wx.LC_REPORT|wx.LC_SINGLE_SEL|wx.LC_VIRTUAL|wx.LC_EDIT_LABELS|wx.LC_HRULES|wx.LC_VRULES)
        listCtrl.InsertColumn(0, _('Title'))
        listCtrl.InsertColumn(1, _('Frame No.'), wx.LIST_FORMAT_RIGHT)
        listCtrl.InsertColumn(2, _('Time **'))
        listCtrl.SetItemCount(len(bookmarkInfo))
        listCtrl.setResizeColumn(1)
        listCtrl.SetColumnWidth(1, wx.LIST_AUTOSIZE_USEHEADER)
        listCtrl.SetColumnWidth(2, wx.LIST_AUTOSIZE)
        
        def OnListCtrlActivated(event):
            listCtrl.EditLabel(event.GetIndex())
            
        def OnListCtrlEndLabelEdit(event):
            i = event.GetIndex()
            bookmark, timecode, oldTitle = bookmarkInfo[i]
            newTitle = event.GetLabel().strip()
            if bookmark not in historyList:
                if oldTitle and not newTitle:
                    titleList.remove(bookmark)
                if not oldTitle and newTitle:
                    titleList.append(bookmark)
            bookmarkInfo[i] = (bookmark, timecode, newTitle)
            
        listCtrl.Bind(wx.EVT_LIST_ITEM_ACTIVATED, OnListCtrlActivated)
        listCtrl.Bind(wx.EVT_LIST_END_LABEL_EDIT, OnListCtrlEndLabelEdit)
        label = wx.StaticText(dlg, wx.ID_ANY, _('Left-click on a selected item or double-click to edit.\n\n'
                                                '*  RED - a historic title, not a real bookmark.\n'
                                                '** Time may be unavailable or incorrect before preview refreshed.'
                                                ))
        # Standard buttons
        okay  = wx.Button(dlg, wx.ID_OK, _('OK'))
        cancel = wx.Button(dlg, wx.ID_CANCEL, _('Cancel'))
        btns = wx.StdDialogButtonSizer()
        btns.AddButton(okay)
        btns.AddButton(cancel)
        btns.Realize()
        # Size the elements
        dlgSizer = wx.BoxSizer(wx.VERTICAL)
        dlgSizer.Add(listCtrl, 1, wx.EXPAND|wx.ALL, 5)
        dlgSizer.Add(label, 0, wx.LEFT, 5)
        dlgSizer.Add(btns, 0, wx.EXPAND|wx.ALL, 5)
        dlg.SetSizer(dlgSizer)
        ID = dlg.ShowModal()
        if ID == wx.ID_OK:
            for bookmark, timecode, title in bookmarkInfo:
                self.bookmarkDict[bookmark] = title
                if not title:
                    del self.bookmarkDict[bookmark]
            self.UpdateBookmarkMenu()
            if self.previewWindowVisible:
                self.videoSlider.Refresh()
                if self.separatevideowindow:
                    self.videoSlider2.Refresh()
        dlg.Destroy()

    def OnMenuVideoGotoLastScrolled(self, event):
        curPos = self.videoSlider.GetValue()
        self.ShowVideoFrame(self.lastshownframe)
        self.lastshownframe = curPos

    def OnMenuVideoGotoNextBookmark(self, event):
        self.GotoNextBookmark()

    def OnMenuVideoGotoPreviousBookmark(self, event):
        self.GotoNextBookmark(reverse=True)

    def OnMenuVideoGotoClearAll(self, event):
        self.DeleteAllFrameBookmarks(bmtype=0)

    def OnMenuVideoGoto(self, event):
        if not self.separatevideowindow or not self.previewWindowVisible or self.FindFocus() != self.videoWindow:
            frameTextCtrl = self.frameTextCtrl
        else:
            frameTextCtrl = self.frameTextCtrl2
        #~ frameTextCtrl.SetSelection(-1, -1)               
        frameTextCtrl.SetFocus()

    def OnMenuVideoPrevFrame(self, event):
        if not self.separatevideowindow:
            self.ShowVideoOffset(-1)
        else:
            if event is not None and event.GetEventObject() in self.videoControlWidgets and self.previewWindowVisible:
                self.ShowVideoOffset(-1, focus=False)
                self.currentScript.SetFocus()
            else:
                self.ShowVideoOffset(-1)

    def OnMenuVideoNextFrame(self, event):
        if not self.separatevideowindow:
            self.ShowVideoOffset(+1)
        else:
            if event is not None and event.GetEventObject() in self.videoControlWidgets and self.previewWindowVisible:
                self.ShowVideoOffset(+1, focus=False)
                self.currentScript.SetFocus()
            else:
                self.ShowVideoOffset(+1)

    def OnMenuVideoPrevSecond(self, event):
        self.ShowVideoOffset(-1, units='sec')

    def OnMenuVideoNextSecond(self, event):
        self.ShowVideoOffset(+1, units='sec')

    def OnMenuVideoPrevMinute(self, event):
        self.ShowVideoOffset(-1, units='min')

    def OnMenuVideoNextMinute(self, event):
        self.ShowVideoOffset(+1, units='min')

    def OnMenuVideoFirstFrame(self, event):
        self.ShowVideoFrame(0)

    def OnMenuVideoLastFrame(self, event):
        self.ShowVideoFrame(-1)

    def OnMenuVideoPrevCustomUnit(self, event):
        offset = -self.options['customjump']
        units = self.options['customjumpunits']
        self.ShowVideoOffset(offset, units=units)

    def OnMenuVideoNextCustomUnit(self, event):
        offset = +self.options['customjump']
        units = self.options['customjumpunits']
        self.ShowVideoOffset(offset, units=units)

    def OnMenuVideoPlay(self, event):
        self.RunExternalPlayer()

    def OnMenuVideoSaveImage(self, event):
        self.SaveCurrentImage()

    def OnMenuVideoCropEditor(self, event):
        if self.zoomfactor != 1 or self.zoomwindow or self.flip:
            wx.MessageBox(_('Cannot use crop editor unless zoom set to 100% and non-flipped!'), _('Error'), style=wx.OK|wx.ICON_ERROR)
            return False
        script = self.currentScript
        dlg = self.cropDialog
        dlg.boolInvalidCrop = False
        if dlg.IsShown():
            return
        # Show the video preview
        if not self.ShowVideoFrame():
            return False
        # Set the spin control ranges
        w = script.AVI.Width
        h = script.AVI.Height
        for key in ('left', '-right'):
            dlg.ctrls[key].SetRange(0, w-self.options['cropminx'])
            dlg.ctrls[key].SetValue(0)
            dlg.ctrls[key].SetSelection(0,-1)
        for key in ('top', '-bottom'):
            dlg.ctrls[key].SetRange(0, h-self.options['cropminy'])
            dlg.ctrls[key].SetValue(0)
            dlg.ctrls[key].SetSelection(0,-1)
        # Show the crop dialog
        self.SetDialogPositionNextToVideo(dlg)
        self.PaintCropWarnings()
        dlg.Show()
        dlg.ctrls['left'].SetFocus()
        dlg.ctrls['left'].SetSelection(0,-1)
        # Set the crop status text
        self.SetVideoStatusText()

    def SetDialogPositionNextToVideo(self, dlg):
        parent = dlg.GetParent()
        xp, yp = parent.GetPositionTuple()
        wp, hp = parent.GetSizeTuple()
        wd, hd = wx.ScreenDC().GetSizeTuple()
        ws, hs = dlg.GetSizeTuple()
        #~ dlg.SetPosition((min(xp+wp-20, wd-ws),-1))
        xSplitter = self.videoSplitter.GetSashPosition()
        wVideo = self.currentScript.AVI.Width
        xpos = min(xp+wVideo+30, xp+xSplitter+20)
        dlg.SetPosition((min(xpos, wd-ws), yp+hp-hs-self.mainSplitter.GetMinimumPaneSize()-50))

    def OnMenuVideoTrimEditor(self, event):
        dlg = self.trimDialog
        if dlg.IsShown():
            return
        # Show the video preview
        if not self.ShowVideoFrame():
            return False
        self.SetDialogPositionNextToVideo(dlg)
        for slider in self.GetVideoSliderList():
            slider.ToggleSelectionMode(1)
        dlg.Show()
        self.ShowVideoFrame()

    def OnMenuVideoTrimEditorSetStartpoint(self, event):
        self.SetSelectionEndPoint(1)

    def OnMenuVideoTrimEditorSetEndpoint(self, event):
        self.SetSelectionEndPoint(2)

    def OnMenuVideoZoom(self, event, menuItem=None, show=True):
        if True:#wx.VERSION > (2, 8):
            vidmenus = [self.videoWindow.contextMenu, self.GetMenuBar().GetMenu(2)]
            if menuItem is None:
                id = event.GetId()
                for vidmenu in vidmenus:
                    menu = vidmenu.FindItemById(vidmenu.FindItem(_('&Zoom'))).GetSubMenu()
                    menuItem = menu.FindItemById(id)
                    if menuItem:
                        menuItem.Check()
                        label = menuItem.GetLabel()
                        zoomvalue = self.zoomLabelDict[label]
                    else:
                        updateMenu = menu
                id = updateMenu.FindItem(label)
                menuItem = updateMenu.FindItemById(id)
                if menuItem is None:
                    print>>sys.stderr, _('Error'), 'OnMenuVideoZoom(): cannot find menu item by id'
                    return
                menuItem.Check()
            else:
                menuItem.Check()
                label = menuItem.GetLabel()
                zoomvalue = self.zoomLabelDict[label]
                for vidmenu in vidmenus:
                    menu = vidmenu.FindItemById(vidmenu.FindItem(_('&Zoom'))).GetSubMenu()
                    if menu != menuItem.GetMenu():
                        id = menu.FindItem(label)
                        menuItem = menu.FindItemById(id)
                        if menuItem is None:
                            print>>sys.stderr, _('Error'), 'OnMenuVideoZoom(): cannot find menu item by id'
                            return
                        menuItem.Check()
                        break
        else:
            if menuItem is None:
                id = event.GetId()
                vidmenu = self.videoWindow.contextMenu
                menu = vidmenu.FindItemById(vidmenu.FindItem(_('&Zoom'))).GetSubMenu()
                menuItem = menu.FindItemById(id)
            if menuItem is None:
                print>>sys.stderr, _('Error'), 'OnMenuVideoZoom(): cannot find menu item by id'
                return
            menuItem.Check()
            zoomvalue = self.zoomLabelDict[menuItem.GetLabel()]
        if zoomvalue == 'fill':
            self.zoomwindow = True
            self.zoomwindowfit = False
            self.zoomwindowfill = True
            zoomfactor = 1
        elif zoomvalue == 'fit':
            self.zoomwindow = True
            self.zoomwindowfit = True
            self.zoomwindowfill = False
            zoomfactor = 1
        else:
            try:
                zoompercent = int(zoomvalue) #int(label.strip(' %'))
            except ValueError:
                zoompercent = 100
            if zoompercent >= 100:
                zoomfactor = zoompercent / 100
            else:
                if zoompercent == 50:
                    zoomfactor = 0.5
                elif zoompercent == 25:
                    zoomfactor = 0.25
                else:
                    return
            if self.zoomwindow:
                self.zoomwindow = False
                self.zoomwindowfit = False
                self.zoomwindowfill = False
                #~ for index in xrange(self.scriptNotebook.GetPageCount()):
                    #~ script = self.scriptNotebook.GetPage(index)
                    #~ script.AVI = None
                self.currentScript.lastSplitVideoPos = None
        #~ self.ZoomPreviewWindow(zoomfactor, show=show)
        self.zoomfactor = zoomfactor
        if show:
            self.ShowVideoFrame()

    def OnMenuVideoFlip(self, event):
        id = event.GetId()
        if True:#wx.VERSION > (2, 8):
            vidmenus = [self.videoWindow.contextMenu, self.GetMenuBar().GetMenu(2)]
            for vidmenu in vidmenus:
                menu = vidmenu.FindItemById(vidmenu.FindItem(_('&Flip'))).GetSubMenu()
                menuItem = menu.FindItemById(id)
                if menuItem: 
                    label = menuItem.GetLabel()
                    value = self.flipLabelDict[label]
                    menuItem.Check(value not in self.flip)
                else:
                    updateMenu = menu
            id = updateMenu.FindItem(label)
            menuItem = updateMenu.FindItemById(id)
            if menuItem is None:
                print>>sys.stderr, _('Error'), 'OnMenuVideoFlip(): cannot find menu item by id'
                return
            menuItem.Check(value not in self.flip)
        else:
            vidmenu = self.videoWindow.contextMenu
            menu = vidmenu.FindItemById(vidmenu.FindItem(_('&Flip'))).GetSubMenu()
            menuItem = menu.FindItemById(id)
            if menuItem is None:
                print>>sys.stderr, _('Error'), 'OnMenuVideoFlip(): cannot find menu item by id'
                return
            value = self.flipLabelDict[menuItem.GetLabel()]            
            menuItem.Check(value not in self.flip)
            
        if value in self.flip:
            self.flip.remove(value)
        else:
            self.flip.append(value)
        self.bmpVideo = None
        self.videoWindow.Refresh()
    
    def OnMenuVideoYUV2RGB(self, event):
        id = event.GetId()
        if True:#wx.VERSION > (2, 8):
            vidmenus = [self.videoWindow.contextMenu, self.GetMenuBar().GetMenu(2)]
            for vidmenu in vidmenus:
                menu = vidmenu.FindItemById(vidmenu.FindItem(_('&YUV -> RGB'))).GetSubMenu()
                menuItem = menu.FindItemById(id)
                if menuItem:
                    label = menuItem.GetLabel()                    
                    value = self.yuv2rgbDict[label]
                    if menuItem.GetKind() == wx.ITEM_RADIO:
                        menuItem.Check()
                    else:
                        menuItem.Check(not getattr(self, value))
                else:
                    updateMenu = menu
            id = updateMenu.FindItem(label)
            menuItem = updateMenu.FindItemById(id)
            if not menuItem:
                print>>sys.stderr, _('Error'), 'OnMenuVideoYUV2RGB(): cannot find menu item by id'
                return
            if menuItem.GetKind() == wx.ITEM_RADIO:
                menuItem.Check()
            else:
                menuItem.Check(not getattr(self, value))
        else:
            vidmenu = self.videoWindow.contextMenu
            menu = vidmenu.FindItemById(vidmenu.FindItem(_('&YUV -> RGB'))).GetSubMenu()
            menuItem = menu.FindItemById(id)
            if menuItem is None:
                print>>sys.stderr, _('Error'), 'OnMenuVideoYUV2RGB(): cannot find menu item by id'
                return
            if menuItem.GetKind() == wx.ITEM_RADIO:
                menuItem.Check()
            else:
                menuItem.Check(not self.swapuv)
            value = self.yuv2rgbDict[menuItem.GetLabel()]
        if value == 'swapuv':
            self.swapuv = not self.swapuv
            if self.currentScript.AVI:
                refresh = self.currentScript.AVI.IsYUV
        elif value in ['Progressive', 'Interlaced']:
            self.interlaced = not self.interlaced
            if self.currentScript.AVI:
                refresh = self.currentScript.AVI.IsYV12
        else:
            self.matrix = value
            if self.currentScript.AVI:
                refresh = self.currentScript.AVI.IsYUV
        if self.previewWindowVisible and refresh:
            self.OnMenuVideoRefresh(event)

    def OnMenuVideoRefresh(self, event):
        self.ShowVideoFrame(forceRefresh=True, forceLayout=True, focus=self.options['focusonrefresh'])

    def OnMenuVideoHide(self, event):
        self.HidePreviewWindow()

    def OnMenuVideoReleaseMemory(self, event):
        self.HidePreviewWindow()
        for index in xrange(self.scriptNotebook.GetPageCount()):
            script = self.scriptNotebook.GetPage(index)
            script.AVI = None

    def OnMenuVideoToggle(self, event):
        if self.previewWindowVisible:
            self.HidePreviewWindow()
            self.SetStatusWidths([-1, 0])
        else:
            self.ShowVideoFrame(resize=True)

    def OnMenuVideoSwitchMode(self, event):
        if self.previewWindowVisible:
            if self.FindFocus() == self.videoWindow:
                self.currentScript.SetFocus()
                self.currentScript.EnsureCaretVisible()
            else:
                self.ShowVideoFrame()
        else:
            self.ShowVideoFrame()

    def OnMenuVideoToggleSliderWindow(self, event):
        #~ self.OnLeftDClickVideoSplitter(None)
        self.ToggleSliderWindow(vidrefresh=True)

    def OnMenuVideoExternalPlayer(self, event):
        self.RunExternalPlayer()
            
    def OnMenuVideoInfo(self, event):
        dlg = wx.Dialog(self, wx.ID_ANY, _('Video information'))
        vi = self.GetVideoInfoDict()
        labels = (
            (_('Video'),
                (
                (_('Frame size:'), '%ix%i (%s)' % (vi['width'], vi['height'], vi['aspectratio'])),
                (_('Length:'), '%i %s (%s)' % (vi['framecount'], _('frames'), vi['totaltime'])),
                (_('Frame rate:'), '%.03f %s (%i/%i)' % (vi['framerate'], _('fps'), vi['frameratenum'], vi['framerateden'])),
                (_('Colorspace:'), vi['colorspace']),
                (_('Field or frame based:'), vi['fieldframebased']),
                (_('Parity:'), vi['parity']),
                ),
            ),
            (_('Audio'),
                (
                (_('Channels:'), '%i' % (vi['audiochannels'])),
                (_('Sampling rate:'), '%i %s' % (vi['audiorate'], _('Hz'))),
                (_('Sample type:'), '%s %i %s' % (vi['audiotype'], vi['audiobits'], _('bits'))),
                (_('Length:'), '%i %s' % (vi['audiolength'], _('samples'))),
                ),
            ),
        )
        # Main items
        sizer = wx.FlexGridSizer(cols=2, hgap=10, vgap=3)
        for sectionLabel, items in labels:
            staticText = wx.StaticText(dlg, wx.ID_ANY, sectionLabel)
            font = staticText.GetFont()
            #~ font.SetPointSize(10)
            font.SetWeight(wx.FONTWEIGHT_BOLD)
            font.SetUnderlined(True)
            staticText.SetFont(font)
            sizer.Add(staticText, 0, wx.TOP, 5)
            sizer.Add((0,0), 0, 0)
            for label, value in items:
                sizer.Add(wx.StaticText(dlg, wx.ID_ANY, '  ' + label), 0, 0)
                sizer.Add(wx.StaticText(dlg, wx.ID_ANY, value), 0, 0)
        # Standard buttons
        okay  = wx.Button(dlg, wx.ID_OK, _('OK'))
        #~ cancel = wx.Button(dlg, wx.ID_CANCEL, _('Cancel'))
        btns = wx.StdDialogButtonSizer()
        btns.AddButton(okay)
        #~ btns.AddButton(cancel)
        btns.Realize()
        dlgSizer = wx.BoxSizer(wx.VERTICAL)
        dlgSizer.Add(sizer, 1, wx.EXPAND|wx.ALL, 5)
        dlgSizer.Add(btns, 0, wx.EXPAND|wx.ALL, 10)
        dlg.SetSizer(dlgSizer)
        dlg.Fit()
        ID = dlg.ShowModal()
        dlg.Destroy()

    def OnMenuMacroRunSelected(self, event):
        id = event.GetId()
        macrofilename = self.macrosImportNames[id]
        menuItem = self.GetMenuBar().GetMenu(self.macroMenuPos).FindItemById(id)
        if menuItem.IsCheckable():
            menu = menuItem.GetMenu()
            self.RenameMacro(menu)
        else:
            self.macrosStack.append(id)
            self.ExecuteMacro(macrofilename)
            self.macrosStack.pop()

    def OnMenuMacrosFolder(self, event):
        if os.path.exists(self.macrofolder):
            os.startfile(self.macrofolder)
        else:
            wx.MessageBox(_('Could not find the macros folder!') % locals(), _('Error'), style=wx.OK|wx.ICON_ERROR)

    def OnMenuMacrosReadme(self, event):
        readme = os.path.join(self.macrofolder, 'macros_readme.txt')
        if os.path.exists(readme):
            os.startfile(readme)
        else:
            wx.MessageBox(_('Could not find %(readme)s!') % locals(), _('Error'), style=wx.OK|wx.ICON_ERROR)

    def OnMenuToolsRunSelected(self, event):
        try:
            os.chdir(self.toolsfolder)
        except:
            pass
        try:
            name = self.toolsImportNames[event.GetId()]
            obj = __import__(name)
        except (ImportError, KeyError):
            wx.MessageBox(_('Failed to import the selected tool'), _('Error'), style=wx.OK|wx.ICON_ERROR)
            return
        avsp = self.ExecuteMacro(return_env=True)
        #~ avsp.GetWindow = lambda: self
        obj.__dict__['avsp'] = avsp
        obj.__dict__['_'] = _
        obj.__dict__['last'] = self.macroVars['last']
        self.macroVars['last'] = obj.avsp_run()

    def OnMenuOptionsAlwaysOnTop(self, event):
        id = event.GetId()
        menuItem = self.GetMenuBar().FindItemById(id)
        if not self.options['alwaysontop']:
            self.options['alwaysontop'] = True
            menuItem.Check(True)
        else:
            self.options['alwaysontop'] = False
            menuItem.Check(False)
        if self.options['alwaysontop']:
            style = wx.DEFAULT_FRAME_STYLE|wx.STAY_ON_TOP
        else:
            style = wx.DEFAULT_FRAME_STYLE
        self.SetWindowStyle(style)

    def OnMenuOptionsSingleInstance(self, event):
        id = event.GetId()
        menuItem = self.GetMenuBar().FindItemById(id)
        if not self.options['singleinstance']:
            self.options['singleinstance'] = True
            menuItem.Check(True)
        else:
            self.options['singleinstance'] = False
            menuItem.Check(False)
        #~ wx.GetApp().boolSingleInstance = self.options['singleinstance']
        #~ self.SetWindowStyle(style)
        wx.MessageBox(_('You must restart for changes to take effect!'), _('Warning'))
        f = open(self.optionsfilename, mode='wb')
        cPickle.dump(self.options, f, protocol=0)
        f.close()

    def OnMenuOptionsFilters(self, event):
        self.ShowFunctionDefinitionDialog()

    def OnMenuOptionsFontsAndColors(self, event):
        dlgInfo = (
            (_('Basic'),
                (
                    (_('Default:'), 'default'),
                    (_('Comment:'), 'comment'),
                    (_('Block Comment:'), 'blockcomment'),
                    (_('__END__ Comment:'), 'endcomment'),
                    (_('Number:'), 'number'),
                    (_('Operator:'), 'operator'),
                    (_('String:'), 'string'),
                    (_('Triple-quoted string:'), 'stringtriple'),
                    (_('Internal filter:'), 'internalfilter'),
                    (_('External filter:'), 'externalfilter'),
                    (_('Internal function:'), 'internalfunction'),
                    (_('User defined function:'), 'userdefined'),
                    (_('Clip property:'), 'clipproperty'),
                    (_('AviSynth keyword:'), 'keyword'),
                    (_('AviSynth data type:'), 'datatype'),
                    (_('AvsP user slider:'), 'userslider'),
                    (_('Monospaced font:'), 'monospaced'),
                ),
            ),
            (_('Advanced'),
                (
                    ((_('Incomplete string:'), 'usestringeol', _('Syntax highlight strings which are not completed in a single line differently')), 'stringeol'),
                    (_('Brace highlight:'), 'bracelight'),
                    (_('Bad brace:'), 'badbrace'),
                    (_('Bad number:'), 'badnumber'),
                    (_('Margin line numbers:'), 'linenumber'),
                    (_('Miscellaneous word:'), 'miscword'),
                    (_('Calltip:'), 'calltip'),
                    (_('Calltip highlight:'), 'calltiphighlight'),
                    (_('Cursor:'), 'cursor'),
                    (_('Selection highlight:'), 'highlight'),
                    ((_('Current line highlight:'), 'highlightline', _('Highlight the line that the caret is currently in')), 'highlightline'),
                    (_('Fold margin:'), 'foldmargin'),
                    (_('Scrap window'), 'scrapwindow'),
                ),
            )
        )
        extra = (_('Use monspaced font'), 'usemonospacedfont', _('Override all fonts to use a specified monospace font(no effect on scrap window)'))
        dlg = AvsStyleDialog(self, dlgInfo, self.options['textstyles'], extra)
        ID = dlg.ShowModal()
        if ID == wx.ID_OK:
            self.options['textstyles'] = dlg.GetDict()
            self.options.update(dlg.GetDict2())
            for index in xrange(self.scriptNotebook.GetPageCount()):
                script = self.scriptNotebook.GetPage(index)
                script.SetUserOptions()
            textCtrl = self.scrapWindow.textCtrl
            textCtrl.StyleSetSpec(stc.STC_STYLE_DEFAULT, self.options['textstyles']['scrapwindow'])
            textCtrl.StyleClearAll()
            textCtrl.StyleSetSpec(stc.STC_P_WORD, "fore:#FF0000,bold")
        dlg.Destroy()

    def OnMenuOptionsTemplates(self, event):
        # Build and show the dialog
        def keyChecker(key):
            msg = None
            if key.startswith('.'):
                msg = '%s\n%s' % (_('Insert aborted:'), _('No dot required in file extension!'))
            return msg
        dlg = wxp.EditStringDictDialog(
            self,
            self.options['templates'],
            title=_('Edit extension-based templates'),
            keyTitle='  '+_('File extension'),
            valueTitle=_('Template'),
            editable=False,
            insertable=True,
            keyChecker=keyChecker,
            about='%s\n%s' % (
                _('This info is used for inserting sources based on file extensions.'),
                _('Any instances of *** in the template are replaced with the filename.')
            )+'\n'+_('(If you want relative paths instead of the full filename, use [***].)'),
        )
        ID = dlg.ShowModal()
        # Set the data
        if ID == wx.ID_OK:
            self.options['templates'] = dlg.GetDict()
        dlg.Destroy()

    def OnMenuOptionsEnableLineByLineUpdate(self, event):
        id = event.GetId()
        menuItem = self.GetMenuBar().FindItemById(id)
        if not self.options['autoupdatevideo']:
            self.options['autoupdatevideo'] = True
            menuItem.Check(True)
        else:
            self.options['autoupdatevideo'] = False
            menuItem.Check(False)

    def OnMenuOptionsDisablePreview(self, event):
        id = event.GetId()
        menuItem = self.GetMenuBar().FindItemById(id)
        #~ splitlabel = menuItem.GetText().split('\t', 1)
        #~ acc = ''
        #~ if len(splitlabel) == 2:
            #~ acc = '\t' + splitlabel[1]
        if not self.options['disablepreview']:
            #~ if self.GetFrameNumber() != 0: #self.previewWindowVisible:
                #~ self.ShowVideoFrame(0)
            self.HidePreviewWindow()
            self.options['disablepreview'] = True
            #~ menuItem.SetText('%s%s' % (_('Video preview disabled'), acc))
            menuItem.Check(True)
            for ctrl in self.videoControlWidgets:
                ctrl.Disable()
                ctrl.Refresh()
        else:
            self.options['disablepreview'] = False
            #~ menuItem.SetText('%s%s' % (_('Disable the video preview'), acc))
            menuItem.Check(False)
            for ctrl in self.videoControlWidgets:
                ctrl.Enable()
                ctrl.Refresh()
    
            
    def OnMenuOptionsMonospaceFont(self, event):
        id = event.GetId()
        menuItem = self.GetMenuBar().FindItemById(id)
        if not self.options['usemonospacedfont']:
            self.options['usemonospacedfont'] = True
            menuItem.Check(True)
        else:
            self.options['usemonospacedfont'] = False
            menuItem.Check(False)
        for index in xrange(self.scriptNotebook.GetPageCount()):
            script = self.scriptNotebook.GetPage(index)
            if self.options['syntaxhighlight']:
                script.SetTextStyles(self.options['textstyles'], self.options['usemonospacedfont'])
            else:
                script.setStylesNoColor()

    def OnMenuOptionsEnableParanoiaMode(self, event):
        id = event.GetId()
        menuItem = self.GetMenuBar().FindItemById(id)
        if not self.options['paranoiamode']:
            self.options['paranoiamode'] = True
            menuItem.Check(True)
        else:
            self.options['paranoiamode'] = False
            menuItem.Check(False)
        f = open(self.optionsfilename, mode='wb')
        cPickle.dump(self.options, f, protocol=0)
        f.close()

    def OnMenuOptionsAssociate(self, event):
        s1 = _('Associating .avs files will write to the windows registry.')
        s2 = _('Do you wish to continue?')
        ret = wx.MessageBox('%s\n\n%s' % (s1, s2), _('Warning'), wx.YES_NO|wx.ICON_EXCLAMATION)
        if ret == wx.YES:
            if hasattr(sys,'frozen'): # run in py2exe binary mode
                value = '"%s" "%%1"' % sys.executable
            else: # run in source mode
                dirname = os.path.dirname(__file__)
                basename = os.path.basename(__file__)
                if not dirname:
                    dirname = os.getcwd()
                script = os.path.join(dirname, basename)
                value = '"%s" "%s" "%%1"' % (sys.executable, script)
            try:
                hkey = _winreg.OpenKey(_winreg.HKEY_CLASSES_ROOT, 'avsfile\\shell\\Open\\command', 0, _winreg.KEY_SET_VALUE)            
                _winreg.SetValue(_winreg.HKEY_CLASSES_ROOT, 'avsfile\\shell\\Open\\command', _winreg.REG_SZ, value)
                _winreg.CloseKey(hkey)
            except WindowsError, e:
                print e
            try:
                hkey = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts\\.avs', 0, _winreg.KEY_SET_VALUE)
                _winreg.DeleteValue(hkey, 'Application')
                _winreg.CloseKey(hkey)
            except WindowsError, e:
                print e
            try:
                hkey = _winreg.OpenKey(_winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts\\.avs\\UserChoice', 0, _winreg.KEY_SET_VALUE)
                _winreg.DeleteKey(_winreg.HKEY_CURRENT_USER, 'Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\FileExts\\.avs\\UserChoice')
                _winreg.CloseKey(hkey)
            except WindowsError, e:
                print e
            

    def OnMenuConfigureShortcuts(self, event):
        #~ exceptionIds = []
        #~ for window, idList in self._shortcutBindWindowDict.items():
            #~ if window != self:
                #~ exceptionIds += idList
        exceptionIds = (
            self.exceptionShortcuts, 
            self.stcShortcuts,
            self.options['reservedshortcuts'], 
            _('Above keys are built-in editing shortcuts. If item is checked,\n'
              'it will not be overrided by a menu shortcut in script window.')
        )
        dlg = wxp.ShortcutsDialog(self, self.options['shortcuts'], exceptionIds=exceptionIds,
                                  submessage=_('* This shortcut is active only when video window has focus.\n'
                                               '~ This shortcut is active only when script window has focus.'))
        ID = dlg.ShowModal()
        # Set the data
        if ID == wx.ID_OK:
            shortcutList, reservedShortcuts = dlg.GetShortcutList()
            for old, new in zip(self.options['shortcuts'], shortcutList):
                if old != new:
                    menuString, shortcut, id = new
                    menuItem = self.GetMenuBar().FindItemById(id)
                    label = menuItem.GetLabel()
                    if shortcut != '':
                        shortcut = u'\t%s\u00a0' % wxp.GetTranslatedShortcut(shortcut)
                    newLabel = '%s%s' % (label, shortcut)
                    menuItem.SetItemLabel(newLabel)
            self.options['shortcuts'] = shortcutList
            self.options['reservedshortcuts'] = reservedShortcuts
            self.bindShortcutsToAllWindows()
        dlg.Destroy()

    def OnMenuOptionsSettings(self, event):
        dlg = wxp.OptionsDialog(self, self.optionsDlgInfo, self.options)
        ID = dlg.ShowModal()
        # Set the data
        if ID == wx.ID_OK:
            self.options = dlg.GetDict()
            for i in xrange(self.scriptNotebook.GetPageCount()):
                script = self.scriptNotebook.GetPage(i)
                script.SetUserOptions()
                if not self.options['usetabimages']:
                    self.scriptNotebook.SetPageImage(i, -1)            
            self.SetProgramTitle()
            style = wx.NO_BORDER
            if self.options['multilinetab']:
                style |= wx.NB_MULTILINE
            if self.options['fixedwidthtab']:
                style |= wx.NB_FIXEDWIDTH
            self.scriptNotebook.SetWindowStyleFlag(style)
            # a workaroud for multiline notebook issue
            w, h = self.scriptNotebook.GetSize()
            self.scriptNotebook.SetSize((w, h-1))
            self.scriptNotebook.SetSize((w, h))
        dlg.Destroy()

    def OnMenuHelpAvisynth(self, event):
        helpfile = self.options['avisynthhelpfile']
        if helpfile.startswith('%avisynthdir%\\'):
            helpfile = os.path.join(self.options['avisynthdir'], helpfile.split('%avisynthdir%\\')[1])

        # First see if the given doc path exists on the computer
        if os.path.isfile(helpfile):
            os.startfile(helpfile)
            return True
        # Then see if the given doc path is a url
        if helpfile.startswith('http://'):
            os.startfile(helpfile)
            return True
        # Give a message if not a file or a url
        wx.MessageBox('Could not find avisynth help file!', _('Error'), style=wx.OK|wx.ICON_ERROR)

    def OnMenuHelpAvisynthPlugins(self, event):
        plugindir = self.options['recentdirPlugins']
        if not os.path.isdir(plugindir):
            plugindir = os.path.join(self.options['avisynthdir'], 'plugins')
        if os.path.exists(plugindir):
            os.startfile(plugindir)
        else:
            wx.MessageBox(_('Could not find the Avisynth plugins folder!') % locals(), _('Error'), style=wx.OK|wx.ICON_ERROR)

    def OnMenuHelpAnimatedTutorial(self, event):
        filename = os.path.join(self.options['helpdir'], 'Demo.htm')
        if os.path.isfile(filename):
            os.startfile(filename)
        else:
            os.startfile('http://www.avisynth.org/qwerpoi/Demo.htm')

    def OnMenuHelpTextFeatures(self, event):
        filename = os.path.join(self.options['helpdir'], 'Text.html')
        if os.path.isfile(filename):
            os.startfile(filename)
        else:
            os.startfile('http://avisynth.org/qwerpoi/Text.html')

    def OnMenuHelpVideoFeatures(self, event):
        filename = os.path.join(self.options['helpdir'], 'Video.html')
        if os.path.isfile(filename):
            os.startfile(filename)
        else:
            os.startfile('http://avisynth.org/qwerpoi/Video.html')

    def OnMenuHelpUserSliderFeatures(self, event):
        filename = os.path.join(self.options['helpdir'], 'UserSliders.html')
        if os.path.isfile(filename):
            os.startfile(filename)
        else:
            os.startfile('http://avisynth.org/qwerpoi/UserSliders.html')

    def OnMenuHelpMacroFeatures(self, event):
        filename = os.path.join(self.options['helpdir'], 'Macros.html')
        if os.path.isfile(filename):
            os.startfile(filename)
        else:
            os.startfile('http://avisynth.org/qwerpoi/Macros.html')

    def OnMenuHelpReadme(self, event):
        readme = os.path.join(self.programdir, 'readme.txt')
        if os.path.exists(readme):
            os.startfile(readme)
        else:
            wx.MessageBox(_('Could not find %(readme)s!') % locals(), _('Error'), style=wx.OK|wx.ICON_ERROR)

    def OnMenuHelpAbout(self, event):
        version = self.version
        dlg = wx.Dialog(self, wx.ID_ANY, _('About AvsPmod'), size=(220,180))
        bmp = AvsP_icon.getBitmap()
        logo = wx.StaticBitmap(dlg, wx.ID_ANY, bmp)
        title = wx.StaticText(dlg, wx.ID_ANY, _('AvsPmod version %(version)s ') % locals())
        font = title.GetFont()
        font.SetPointSize(12)
        font.SetWeight(wx.FONTWEIGHT_BOLD)
        title.SetFont(font)
        description = wx.StaticText(dlg, wx.ID_ANY, _('An AviSynth script editor'))
        link = wx.StaticText(dlg, wx.ID_ANY, _('AvsP Website'))
        font = link.GetFont()
        font.SetUnderlined(True)
        link.SetFont(font)
        link.SetForegroundColour(wx.Colour(0,0,255))
        link.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        url = 'http://www.avisynth.org/qwerpoi/'
        def OnClick(event):
            os.startfile(url)
        link.SetToolTip(wx.ToolTip(url))
        link.Bind(wx.EVT_LEFT_DOWN, OnClick)
        
        link1 = wx.StaticText(dlg, wx.ID_ANY, _("Active thread on Doom9's forum"))
        font = link1.GetFont()
        font.SetUnderlined(True)
        link1.SetFont(font)
        link1.SetForegroundColour(wx.Colour(0,0,255))
        link1.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        url1 = 'http://forum.doom9.org/showthread.php?t=153248'
        def OnClick1(event):
            os.startfile(url1)
        link1.SetToolTip(wx.ToolTip(url1))
        link1.Bind(wx.EVT_LEFT_DOWN, OnClick1)
        
        staticText = wx.StaticText(dlg, wx.ID_ANY, _('This program is freeware under the GPL license.'))
        url2 = 'http://www.gnu.org/copyleft/gpl.html'
        link2 = wx.StaticText(dlg, wx.ID_ANY, url2)
        font = link2.GetFont()
        font.SetUnderlined(True)
        link2.SetFont(font)
        link2.SetForegroundColour(wx.Colour(0,0,255))
        link2.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        def OnClick2(event):
            os.startfile(url2)
        link2.SetToolTip(wx.ToolTip(url2))
        link2.Bind(wx.EVT_LEFT_DOWN, OnClick2)

        button = wx.Button(dlg, wx.ID_OK, _('OK'))
        inner = wx.BoxSizer(wx.HORIZONTAL)
        inner.Add(logo, 0, wx.LEFT, 15)
        inner.Add(title, 0, wx.ALIGN_CENTER|wx.LEFT, 10)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(inner, 0, wx.TOP, 20)
        sizer.Add(description, 0, wx.ALIGN_CENTER|wx.ALL, 10)
        sizer.Add(link, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        sizer.Add(link1, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        sizer.Add((0,5), 0, wx.EXPAND)
        sizer.Add(wx.StaticLine(dlg), 0, wx.EXPAND|wx.TOP, 10)
        sizer.Add(staticText, 0, wx.EXPAND|wx.ALIGN_CENTER|wx.ALL, 5)
        sizer.Add(link2, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        sizer.Add(button, 0, wx.ALIGN_CENTER|wx.ALL, 5)
        dlg.SetSizer(sizer)
        dlg.Layout()
        dlg.Fit()
        dlg.ShowModal()
        dlg.Destroy()

    def OnButtonTextSetFocus(self, event):
        self.SetStatusText(_('Input a frame number or time (hr:min:sec) and hit Enter. Right-click to retrieve from history.'))
        frameTextCtrl = event.GetEventObject()
        frameTextCtrl.SetForegroundColour(wx.BLACK)
        wx.CallAfter(frameTextCtrl.SetSelection, -1, -1)
        event.Skip()

    def OnButtonTextKillFocus(self, event):
        frameTextCtrl = event.GetEventObject()
        txt = frameTextCtrl.GetLineText(0)
        if txt and txt not in self.recentframes:
            self.recentframes.append(txt)
        win = self.FindFocus()
        if  win != frameTextCtrl:
            frame = self.videoSlider.GetValue()
            if (frame, 0) in self.GetBookmarkFrameList():
                color = wx.RED
            else:
                color = wx.BLACK
            self.frameTextCtrl.SetForegroundColour(color)
            self.frameTextCtrl.Replace(0, -1, str(frame))
            return
        try:
            frame = int(txt)
        except ValueError:
            timetxt = txt.split(':')
            if len(timetxt) == 2:
                timetxt.insert(0, 0)
            try:
                if len(timetxt) != 3: raise
                hours = int(timetxt[0])
                if hours < 0: raise
                minutes = int(timetxt[1])
                if minutes < 0 or minutes >= 60: raise
                seconds = float(timetxt[2])
                if seconds < 0 or seconds >= 60: raise
                total = hours * 60 * 60 + minutes * 60 + seconds
                frame = int(round(self.currentScript.AVI.Framerate * total))                
            except:
                frame = -2
        if frame == -1:
            frame = self.currentScript.AVI.Framecount - 1
        if frame < 0 or (self.currentScript.AVI and frame >= self.currentScript.AVI.Framecount):
            wx.Bell()
            return
        if not self.separatevideowindow:
            self.ShowVideoFrame(frame)
        else:
            if event is not None and event.GetEventObject() in self.videoControlWidgets and self.previewWindowVisible:
                self.ShowVideoFrame(frame, focus=False)
                self.currentScript.SetFocus()
            else:
                self.ShowVideoFrame(frame)
        
    def OnButtonTextContextMenu(self, event):
        textCtrl = event.GetEventObject()
        menu = wx.Menu()
        def OnContextMenuCopyTime(event):
            frame = self.GetFrameNumber()
            try:
                m, s = divmod(frame/self.MacroGetVideoFramerate(), 60)
            except:
                return
            h, m = divmod(m, 60)
            timecode = '%02d:%02d:%06.3f' % (h ,m, s)
            if not wx.TheClipboard.IsOpened():
                wx.TheClipboard.Open()
                wx.TheClipboard.SetData(wx.TextDataObject(timecode))
                wx.TheClipboard.Close()

        def OnContextMenuCopy(event):
            text = textCtrl.GetStringSelection()
            if not text:
                text = textCtrl.GetLineText(0)
            if text and not wx.TheClipboard.IsOpened():
                wx.TheClipboard.Open()
                wx.TheClipboard.SetData(wx.TextDataObject(text))
                wx.TheClipboard.Close()
                
        def OnContextMenuPaste(event):
            if not wx.TheClipboard.IsOpened():
                wx.TheClipboard.Open()
                text = wx.TextDataObject('')
                if wx.TheClipboard.GetData(text):
                    text = text.GetText()
                    if text:
                        frm, to = textCtrl.GetSelection()
                        if textCtrl.FindFocus() != textCtrl:
                            frm, to = 0, -1
                        textCtrl.Replace(frm, to, text)                                                
                        textCtrl.SetFocus()
                wx.TheClipboard.Close()
                
        def OnContextMenuClear(event):
            self.recentframes = []
                
        def OnContextMenuItem(event):
            item = menu.FindItemById(event.GetId())
            textCtrl.Replace(0, -1, item.GetItemLabelText())
            textCtrl.SetFocus()
            
        for text in self.recentframes:
            id = wx.NewId()
            self.Bind(wx.EVT_MENU, OnContextMenuItem, id=id)
            menu.Append(id, text)
        menu.AppendSeparator()
        id = wx.NewId()
        self.Bind(wx.EVT_MENU, OnContextMenuCopyTime, id=id)
        menu.Append(id, _('copy as time'))
        id = wx.NewId()
        self.Bind(wx.EVT_MENU, OnContextMenuCopy, id=id)
        menu.Append(id, _('copy'))
        id = wx.NewId()
        self.Bind(wx.EVT_MENU, OnContextMenuPaste, id=id)
        menu.Append(id, _('paste'))
        id = wx.NewId()
        self.Bind(wx.EVT_MENU, OnContextMenuClear, id=id)
        menu.Append(id, _('clear history'))
        self.PopupMenu(menu)
        menu.Destroy()

    def OnSliderChanged(self, event):
        videoSlider = event.GetEventObject()
        frame = videoSlider.GetValue()
        if (frame, 0) in self.GetBookmarkFrameList():
            color = wx.RED
        else:
            color = wx.BLACK
        self.frameTextCtrl.SetForegroundColour(color)
        self.frameTextCtrl.Replace(0, -1, str(frame))
        if self.separatevideowindow:
            self.frameTextCtrl2.SetForegroundColour(color)
            self.frameTextCtrl2.Replace(0, -1, str(frame))
        self.SetVideoStatusText()
        if self.options['dragupdate']:
            self.lastshownframe = self.paintedframe
            if not self.separatevideowindow:
                self.ShowVideoFrame(frame)
            else:
                if event is not None and event.GetEventObject() in self.videoControlWidgets and self.previewWindowVisible:
                    self.ShowVideoFrame(frame, focus=False)
                    self.currentScript.SetFocus()
                else:
                    self.ShowVideoFrame(frame)
        #~ self.videoWindow.SetFocus()

    def OnSliderReleased(self, event):
        videoSlider = event.GetEventObject()
        frame = videoSlider.GetValue()
        self.lastshownframe = self.paintedframe
        #~ if self.FindFocus() != videoSlider:
            #~ return
        if not self.separatevideowindow:
            self.ShowVideoFrame(frame)
        else:
            if event is not None and event.GetEventObject() in self.videoControlWidgets and self.previewWindowVisible:
                self.ShowVideoFrame(frame, focus=False)
                self.currentScript.SetFocus()
            else:
                self.ShowVideoFrame(frame)
        self.videoWindow.SetFocus()

    def OnSliderRightUp(self, event):
        slider = event.GetEventObject()
        mousepos = event.GetPosition()
        if slider.HitTestHandle(mousepos):
            frame = slider.GetValue()
            self.AddFrameBookmark(frame, toggle=True)
            colors = [wx.RED, wx.BLACK]
            colors.remove(self.frameTextCtrl.GetForegroundColour())
            self.frameTextCtrl.SetForegroundColour(colors[0])
            self.frameTextCtrl.Refresh()
            if self.separatevideowindow:
                self.frameTextCtrl2.SetForegroundColour(colors[0])
                self.frameTextCtrl2.Refresh()
            if colors[0] == wx.BLACK and frame in self.bookmarkDict and (event.ControlDown() or event.AltDown() or event.ShiftDown()):
                del self.bookmarkDict[frame]
        #~ else:
            #~ index = slider.HitTestBookmark(mousepos)
            #~ if index is not None:
                #~ bookmarks = slider.GetBookmarks()
                #~ value, bmtype = bookmarks[index]
                #~ bmtype += 1
                #~ if bmtype > 2:
                    #~ bmtype = 0
                #~ self.AddFrameBookmark(value, bmtype, toggle=False)
        event.Skip()

    def OnSliderMiddleDown(self, event):
        slider = event.GetEventObject()
        mousepos = event.GetPosition()
        index = slider.HitTestBookmark(mousepos)
        if index is not None:
            bookmarks = slider.GetBookmarks()
            value, bmtype = bookmarks[index]
            self.DeleteFrameBookmark(value, bmtype)            
            if value in self.bookmarkDict and (event.ControlDown() or event.AltDown() or event.ShiftDown()):
                del self.bookmarkDict[value]
            self.frameTextCtrl.SetForegroundColour(wx.BLACK)
            self.frameTextCtrl.Refresh()
            if self.separatevideowindow:
                self.frameTextCtrl2.SetForegroundColour(wx.BLACK)
                self.frameTextCtrl2.Refresh()

    def OnSliderLeftUp(self, event):
        slider = event.GetEventObject()
        mousepos = event.GetPosition()
        # If clicked on a selection button, create the selection bookmark
        bmtype = slider.HitTestSelectionButton(mousepos)
        if bmtype is not None:
            value = self.GetFrameNumber()
            bookmarks = self.GetBookmarkFrameList()
            self.AddFrameBookmark(value, bmtype)
            #~ if bookmarks.count((value, bmtype)) == 0:
                #~ self.AddFrameBookmark(value, bmtype)
            #~ else:
                #~ slider.RemoveBookmark(value, bmtype)
        event.Skip()

    def OnNotebookPageChanged(self, event):
        # Get the newly selected script
        script = self.scriptNotebook.GetPage(event.GetSelection())
        if not script.previewtxt:
            script.Colourise(0, script.GetTextLength())
        # Set some related key variables (affects other functions)
        self.currentScript = script
        self.refreshAVI = True

        oldSliderWindow = self.currentSliderWindow
        newSliderWindow = script.sliderWindow
        oldSliderWindow.Hide()
        self.currentSliderWindow = newSliderWindow

        # Determine whether to hide the preview or not
        if self.previewWindowVisible:
            forceRefresh = False
            if self.zoomwindow:
                #~ if script.lastSplitVideoPos != self.lastSplitVideoPos:
                    #~ forceRefresh=True
                pass
            #~ if self.zoomwindowfit:
                #~ forceRefresh=True
            if self.UpdateScriptAVI(script, forceRefresh=forceRefresh, prompt=True) is None:
                self.HidePreviewWindow()
                return False
            if (script.AVI.WidthActual, script.AVI.HeightActual) == self.oldVideoSize:
                script.lastSplitVideoPos = self.oldLastSplitVideoPos
                boolSliders = bool(script.sliderTexts or script.sliderProperties or script.toggleTags or script.autoSliderInfo)
                #~ if boolSliders and self.oldBoolSliders:
                if boolSliders and self.oldBoolSliders:
                    #~ if not script.sliderWindowShown and self.oldSliderWindowShown:
                        #~ script.sliderWindowShown = True
                    if self.oldSliderWindowShown != script.sliderWindowShown:
                        script.sliderWindowShown = self.oldSliderWindowShown
                    if self.oldSliderWindowShown is True and script.sliderWindowShown is True:
                        script.lastSplitSliderPos = self.oldLastSplitSliderPos
                    #~ elif self.oldSliderWindowShown != script.sliderWindowShown:
                        #~ script.sliderWindowShown = self.oldSliderWindowShown
                if script.AVI.Framecount == self.videoSlider.GetMax()+1:
                    script.lastFramenum = None
            if self.zoomwindowfit:
                script.lastSplitVideoPos = self.oldLastSplitVideoPos
                #~ self.ShowVideoFrame(forceRefresh=True, focus=False)
                #~ self.IdleCall = (self.ShowVideoFrame, tuple(), {'forceRefresh': True, 'focus': False})
                self.IdleCall.append((self.ShowVideoFrame, tuple(), {'focus': False}))
            else:
                self.ShowVideoFrame(forceLayout=True, focus=False)
            #~ if script.sliderWindowShown != self.oldSliderWindowShown:
                #~ # Force a reset
                #~ script.sliderWindowShown = not script.sliderWindowShown
                #~ self.ToggleSliderWindow()
                #~ if script.sliderWindowShown:
                    #~ newSliderWindow.Show()
            if not script.sliderWindowShown:
                self.HideSliderWindow(script)
            else:
                newSliderWindow.Show()
                self.ShowSliderWindow(script)

        #~ # Update visuals...
        #~ if script.sliderWindowShown:
            #~ newSliderWindow.Show()
            #~ if self.videoSplitter.IsSplit():# and self.videoSplitter.GetWindow2() == oldSliderWindow:
                #~ self.videoSplitter.ReplaceWindow(oldSliderWindow, newSliderWindow)
            #~ else:
                #~ self.videoSplitter.SplitVertically(self.videoWindow, newSliderWindow, script.lastSplitSliderPos)


        # Misc
        #~ if not self.previewWindowVisible:
            #~ script.SetFocus()
        if self.boolVideoWindowFocused:
            self.videoWindow.SetFocus()
        elif hasattr(script, 'frdlg'):
            script.frdlg.SetFocus()
        else:
            script.SetFocus()
        self.SetProgramTitle()
        self.oldlinenum = None

    def OnNotebookPageChanging(self, event):
        if self.cropDialog.IsShown():
            wx.MessageBox(_('Cannot switch tabs while crop editor is open!'), _('Error'), style=wx.OK|wx.ICON_ERROR)
            event.Veto()
        if self.trimDialog.IsShown():
            wx.MessageBox(_('Cannot switch tabs while trim editor is open!'), _('Error'), style=wx.OK|wx.ICON_ERROR)
            event.Veto()
        if self.FindFocus() == self.videoWindow:
            self.boolVideoWindowFocused = True
        else:
            self.boolVideoWindowFocused = False
        if self.previewWindowVisible:
            oldSelectionIndex = event.GetOldSelection()
            if oldSelectionIndex >= 0:
                oldScript = self.scriptNotebook.GetPage(oldSelectionIndex)
                if oldScript.lastSplitVideoPos is not None:
                    self.oldLastSplitVideoPos = oldScript.lastSplitVideoPos
                else:
                    self.oldLastSplitVideoPos = oldScript.lastSplitVideoPos
                    #~ self.oldLastSplitVideoPos = self.mainSplitter.GetSashPosition() - self.mainSplitter.GetClientSize()[1]
                self.oldLastSplitSliderPos = oldScript.lastSplitSliderPos
                self.oldSliderWindowShown = oldScript.sliderWindowShown
                self.oldBoolSliders = bool(oldScript.sliderTexts or oldScript.sliderProperties or oldScript.toggleTags or oldScript.autoSliderInfo)
                self.oldVideoSize = (oldScript.AVI.WidthActual, oldScript.AVI.HeightActual)
            else:
                self.oldLastSplitVideoPos = None
                self.oldLastSplitSliderPos = None
                self.oldBoolSliders = None
                self.oldVideoSize = (None, None)

    def OnMiddleDownNotebook(self, event):
        ipage = self.scriptNotebook.HitTest(event.GetPosition())[0]
        if ipage != wx.NOT_FOUND:
            self.CloseTab(ipage, boolPrompt=True)
            
    def OnLeftDownNotebook(self, event):
        pos = event.GetPosition()
        ipage = self.scriptNotebook.HitTest(pos)[0]
        if ipage == self.scriptNotebook.GetSelection():
            wx.CallLater(300, self.OnMenuFileRenameTab, ipage, pos)
        event.Skip()
            
    def OnLeftUpNotebook(self, event):
        if self.scriptNotebook.HasCapture():
            self.scriptNotebook.ReleaseMouse()
            self.scriptNotebook.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))
            if not self.scriptNotebook.dblClicked:
                index = self.scriptNotebook.GetSelection()
                ipage = self.scriptNotebook.HitTest(event.GetPosition())[0]
                if ipage != wx.NOT_FOUND and ipage != index:
                    self.RepositionTab(ipage)
        event.Skip()
            
    def OnLeftDClickNotebook(self, event):
        if self.titleEntry:
            return
        self.scriptNotebook.dblClicked = True
        ipage = self.scriptNotebook.HitTest(event.GetPosition())[0]
        if ipage != wx.NOT_FOUND:
            #~ self.CloseTab(ipage, boolPrompt=True)
            self.CopyTextToNewTab(ipage)
            #~ script, index = self.getScriptAtIndex(ipage)
            #~ text = script.GetText()
            #~ self.NewTab(copyselected=False, select=False)
            #~ self.currentScript.SetText(text)
            #~ self.currentScript.SelectAll()
            #~ self.refreshAVI = True
            #~ self.scriptNotebook.SetSelection(self.scriptNotebook.GetPageCount()-1)

    def OnRightClickNotebook(self, event):
        win = event.GetEventObject()
        pos = event.GetPosition()
        ipage = self.scriptNotebook.HitTest(pos)[0]
        if ipage != wx.NOT_FOUND:
            script, index = self.getScriptAtIndex(ipage)
            try:
                menu = win.contextMenu
                self.scriptNotebook.SetSelection(index)
                menuItem = menu.FindItemByPosition(menu.GetMenuItemCount()-1)
                menu = menuItem.GetSubMenu()
                for i in range(menu.GetMenuItemCount()):
                    menu.DestroyItem(menu.FindItemByPosition(0))
                for i in range(self.scriptNotebook.GetPageCount()):
                    label = self.scriptNotebook.GetPageText(i).lstrip('* ')
                    menuItem = menu.Insert(i, wx.ID_ANY, label)                
                    if i != index:
                        self.Bind(wx.EVT_MENU, self.RepositionTab, menuItem)
                    else:
                        menuItem.Enable(False)
                win.PopupMenu(win.contextMenu, pos)
            except AttributeError:
                pass
                
    def OnMouseMotionNotebook(self, event):
        if event.Dragging():
            if self.titleEntry:
                self.scriptNotebook.SetFocus()
            if not self.scriptNotebook.HasCapture():
                self.scriptNotebook.CaptureMouse()
            index = self.scriptNotebook.GetSelection()
            ipage = self.scriptNotebook.HitTest(event.GetPosition())[0]
            if ipage != wx.NOT_FOUND:
                self.scriptNotebook.SetCursor(wx.CursorFromImage(dragdrop_cursor.GetImage()))
            else:
                self.scriptNotebook.SetCursor(wx.StockCursor(wx.CURSOR_NO_ENTRY))
        elif self.scriptNotebook.HasCapture():
            self.scriptNotebook.ReleaseMouse()
            self.scriptNotebook.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))

    def OnLeftDClickWindow(self, event):
        x, y = event.GetPosition()
        #~ if y < self.mainSplitter.GetMinimumPaneSize():
        if y < self.currentScript.GetPosition().y:
            self.NewTab()
        else:
            lo = self.mainSplitter.GetSashPosition()
            hi = lo + self.mainSplitter.GetSashSize()
            if y > lo and y < hi and self.mainSplitter.IsSplit():
                #~ self.SplitVideoWindow(forcefit=True)
                self.currentScript.lastSplitVideoPos = None
                if not self.zoomwindow:
                    self.LayoutVideoWindows(forcefit=True)
                else:
                    self.LayoutVideoWindows(forcefit=True)
                    #~ self.ShowVideoFrame(forceRefresh=True)
                    self.ShowVideoFrame()

    def OnLeftDClickVideoSplitter(self, event):
        #~ self.ToggleSliderWindow(vidrefresh=True)
        pos = self.currentScript.videoSidebarSizer.CalcMin()[0] + 6
        self.videoSplitter.SetSashPosition(-pos)
        self.currentScript.lastSplitSliderPos = self.videoSplitter.GetSashPosition()

    def OnMiddleDownScriptWindow(self, event):
        script = self.currentScript
        xypos = event.GetPosition()
        script.GotoPos(script.PositionFromPoint(xypos))
        self.middleDownScript = True

    def OnMiddleUpScriptWindow(self, event):
        if self.middleDownScript:
            self.InsertSource()
            self.middleDownScript = False

    def OnKeyDownVideoWindow(self, event):
        key = event.GetKeyCode()
        #~ if False:
            #~ pass
        #~ if key == wx.WXK_LEFT:
            #~ self.OnMenuVideoPrevFrame(None)
        #~ elif key == wx.WXK_RIGHT:
            #~ self.OnMenuVideoNextFrame(None)
        #~ elif key == wx.WXK_UP:
            #~ self.OnMenuVideoPrevSecond(None)
        #~ elif key == wx.WXK_DOWN:
            #~ self.OnMenuVideoNextSecond(None)
        #~ elif key in (wx.WXK_PRIOR, wx.WXK_PAGEUP):
            #~ self.OnMenuVideoPrevMinute(None)
        #~ elif key in (wx.WXK_NEXT, wx.WXK_PAGEDOWN):
            #~ self.OnMenuVideoNextMinute(None)
        #~ elif key == wx.WXK_HOME:
            #~ self.ShowVideoFrame(0)
        #~ elif key == wx.WXK_END:
            #~ self.ShowVideoFrame(-1)
        if key in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
            if self.cropDialog.IsShown():
                self.OnCropDialogApply(None)
            elif self.trimDialog.IsShown():
                self.OnTrimDialogApply(None)
            else:
                event.Skip()
        elif key == wx.WXK_ESCAPE:
            if self.cropDialog.IsShown():
                self.OnCropDialogCancel(None)
            elif self.trimDialog.IsShown():
                self.OnTrimDialogCancel(None)
            else:
                event.Skip()
        #~ elif key == wx.WXK_HOME:
            #~ if self.trimDialog.IsShown():
                #~ self.SetSelectionEndPoint(1)
        #~ elif key == wx.WXK_END:
            #~ if self.trimDialog.IsShown():
                #~ self.SetSelectionEndPoint(2)
        elif key >= wx.WXK_NUMPAD0 and key <= wx.WXK_NUMPAD9:
            i = (key - wx.WXK_NUMPAD1 + 10) % 10
            self.SelectTab(index=i)
        elif key >= ord('0') and key <= ord('9'):
            i = (key - ord('1') + 10) % 10
            self.SelectTab(index=i)
        else:
            event.Skip()

    def OnMouseWheelVideoWindow(self, event):
        if not self.options['enabletabscrolling']:
            return
        if event.GetWheelRotation() > 0:
            delta = -1
        else:
            delta = 1
        # Create list of indices to loop through
        index = self.scriptNotebook.GetSelection()
        r = range(self.scriptNotebook.GetPageCount())
        if delta == 1:
            for i in xrange(index+1):
                j = r.pop(0)
                r.append(j)
        else:
            r.reverse()
            for i in xrange(index):
                j = r.pop()
                r.insert(0,j)
        # Loop through r to find next suitable tab
        curframe = self.videoSlider.GetValue()
        oldWidth = self.oldWidth
        oldHeight = self.oldHeight
        oldFramecount = self.oldFramecount
        oldInfo = (self.oldWidth, self.oldHeight, self.oldFramecount)
        for index in r:
            script = self.scriptNotebook.GetPage(index)
            self.refreshAVI = True
            if self.UpdateScriptAVI(script, prompt=True) is None:
                try:
                    if not script.AVI.initialized:
                        continue
                except AttributeError:
                    return False
            newInfo = (
                int(script.AVI.Width * self.zoomfactor),
                int(script.AVI.Height * self.zoomfactor),
                script.AVI.Framecount
            )
            if newInfo == oldInfo:
            #~ if script.AVI and script.AVI.Width == oldWidth and script.AVI.Height == oldHeight and script.AVI.Framecount == oldFramecount:
                self.SelectTab(index)
                break

    def OnMiddleDownVideoWindow(self, event):
        self.HidePreviewWindow()

    def OnLeftDownVideoWindow(self, event):
        if self.cropDialog.IsShown():
            # Set focus on video window if necessary
            # Set trim values if clicked within video frame
            script = self.currentScript
            w = script.AVI.Width
            h = script.AVI.Height
            left = self.cropValues['left']
            top = self.cropValues['top']
            mright = self.cropValues['-right']
            mbottom = self.cropValues['-bottom']
            xPos, yPos = self.videoWindow.CalcUnscrolledPosition(event.GetX(), event.GetY())
            xPos -= self.xo
            yPos -= self.yo
            xcenter = (w - left - mright) / 2 + left
            ycenter = (h - top - mbottom)/2 + top
            xdist = xcenter - xPos
            ydist = ycenter - yPos
            disttop = (xdist ** 2 + (top - yPos) ** 2) ** 0.5
            distbottom = (xdist ** 2 + (h - mbottom - yPos) ** 2) ** 0.5
            distleft = (ydist ** 2 + (left - xPos) ** 2) ** 0.5
            distright = (ydist ** 2 + (w - mright - xPos) ** 2) ** 0.5
            mindist = min(disttop, distbottom, distleft, distright)
            if disttop == mindist:
                top = yPos
                if (h - mbottom) - top < self.options['cropminy']:
                    top = (h - mbottom) - self.options['cropminy']
                self.cropDialog.ctrls['top'].SetValue(top)
                self.lastcrop = 'top'
            elif distbottom == mindist:
                mbottom = h - yPos
                if (h - mbottom) - top < self.options['cropminy']:
                    mbottom = h - top - self.options['cropminy']
                self.cropDialog.ctrls['-bottom'].SetValue(mbottom)
                self.lastcrop = '-bottom'
            elif distleft == mindist:
                left = xPos
                if (w - mright) - left < self.options['cropminx']:
                    left = (w - mright)  - self.options['cropminx']
                self.cropDialog.ctrls['left'].SetValue(left)
                self.lastcrop = 'left'
            elif distright == mindist:
                mright = w - xPos
                if (w - mright) - left < self.options['cropminx']:
                    mright = w - left  - self.options['cropminx']
                self.cropDialog.ctrls['-right'].SetValue(mright)
                self.lastcrop = '-right'
            self.SetVideoStatusText()
            if wx.VERSION > (2, 9):
                self.OnCropDialogSpinTextChange()
        else:
            if self.refreshAVI:
                self.ShowVideoFrame()
            videoWindow = self.videoWindow
            videoWindow.CaptureMouse()
            videoWindow.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
            videoWindow.oldPoint = event.GetPosition()
            videoWindow.oldOrigin = videoWindow.GetViewStart()
        event.Skip()

    def OnMouseMotionVideoWindow(self, event=None):
        if self.cropDialog.IsShown() and event and event.LeftIsDown():
            script = self.currentScript
            w = script.AVI.Width
            h = script.AVI.Height
            left = self.cropValues['left']
            top = self.cropValues['top']
            mright = self.cropValues['-right']
            mbottom = self.cropValues['-bottom']
            xPos, yPos = self.videoWindow.CalcUnscrolledPosition(event.GetX(), event.GetY())
            xPos -= self.xo
            yPos -= self.yo
            if self.lastcrop == 'top':
                top = yPos
                if top < 0:
                    top = 0
                if (h - mbottom) - top < self.options['cropminy']:
                    top = (h - mbottom) - self.options['cropminy']
                self.cropDialog.ctrls['top'].SetValue(top)
            elif self.lastcrop == '-bottom':
                mbottom = h - yPos
                if mbottom < 0:
                    mbottom = 0
                if (h - mbottom) - top < self.options['cropminy']:
                    mbottom = h - top - self.options['cropminy']
                self.cropDialog.ctrls['-bottom'].SetValue(mbottom)
            elif self.lastcrop == 'left':
                left = xPos
                if left < 0:
                    left = 0
                if (w - mright) - left < self.options['cropminx']:
                    left = (w - mright)  - self.options['cropminx']
                self.cropDialog.ctrls['left'].SetValue(left)
            elif self.lastcrop == '-right':
                mright = w - xPos
                if mright < 0:
                    mright = 0
                if (w - mright) - left < self.options['cropminx']:
                    mright = w - left  - self.options['cropminx']
                self.cropDialog.ctrls['-right'].SetValue(mright)
            self.SetVideoStatusText()
            if wx.VERSION > (2, 9):
                self.OnCropDialogSpinTextChange()
        else:
            videoWindow = self.videoWindow
            if event and event.Dragging() and event.LeftIsDown() and videoWindow.HasCapture():
                newPoint = event.GetPosition()
                if videoWindow.GetRect().Inside(newPoint):
                    newOriginX = videoWindow.oldOrigin[0] - (newPoint[0] - videoWindow.oldPoint[0])
                    newOriginY = videoWindow.oldOrigin[1] - (newPoint[1] - videoWindow.oldPoint[1])
                    if newOriginX < 0:
                        videoWindow.oldPoint[0] = newPoint[0] - videoWindow.oldOrigin[0]
                        newOriginX = 0
                    if newOriginY < 0:
                        videoWindow.oldPoint[1] = newPoint[1] - videoWindow.oldOrigin[1]
                        newOriginY = 0
                    xwin, ywin = videoWindow.GetClientSize()
                    xvwin, yvwin = videoWindow.GetVirtualSize()
                    xmax = xvwin - xwin
                    ymax = yvwin - ywin
                    if xmax > 0 and newOriginX > xmax:
                        videoWindow.oldPoint[0] = xmax + newPoint[0] - videoWindow.oldOrigin[0]
                        newOriginX = xmax
                    if ymax > 0 and newOriginY > ymax:
                        videoWindow.oldPoint[1] = ymax + newPoint[1] - videoWindow.oldOrigin[1]
                        newOriginY = ymax
                    videoWindow.Scroll(newOriginX, newOriginY)
                else:
                    videoWindow.ReleaseMouse()
                    videoWindow.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))
            elif self.showVideoPixelInfo: #self.options['showvideopixelinfo']:
                if True:#self.FindFocus() == videoWindow:
                    script = self.currentScript
                    w, h = script.AVI.Width, script.AVI.Height
                    dc = wx.ClientDC(videoWindow)
                    dc.SetDeviceOrigin(self.xo, self.yo)
                    try: # DoPrepareDC causes NameError in wx2.9.1 and fixed in wx2.9.2
                        videoWindow.DoPrepareDC(dc)
                    except:
                        videoWindow.PrepareDC(dc)
                    zoomfactor = self.zoomfactor
                    #~ if self.zoomwindow and script.zoomwindow_actualsize is not None:
                        #~ wOld = w
                        #~ w, h = script.zoomwindow_actualsize
                        #~ zoomfactor = wOld / float(w)
                    if zoomfactor != 1:
                        dc.SetUserScale(zoomfactor, zoomfactor)
                    if event:
                        xpos, ypos = event.GetPosition()
                    else:
                        xpos, ypos = videoWindow.ScreenToClient(wx.GetMousePosition())
                    x = dc.DeviceToLogicalX(xpos)
                    y = dc.DeviceToLogicalY(ypos)
                    #~ x, y = min(max(x,0),w-1), min(max(y,0),h-1)
                    rgb = dc.GetPixel(x, y)
                    R,G,B = rgb.Get()
                    A = 0
                    hexcolor = '$%02x%02x%02x' % (R,G,B)
                    Y = 0.257*R + 0.504*G + 0.098*B + 16
                    U = -0.148*R - 0.291*G + 0.439*B + 128
                    V = 0.439*R - 0.368*G - 0.071*B + 128
                    xposScrolled, yposScrolled = self.videoWindow.CalcUnscrolledPosition(xpos,ypos)
                    if 0 <= x < w and 0<= y < h and xposScrolled>=self.xo and yposScrolled>=self.yo:
                        #~ xystring = 'xy = (%i,%i)' % (x,y)
                        #~ format = self.options['pixelcolorformat']
                        #~ if format == 'rgb':
                            #~ colorstring = 'rgb = (%i,%i,%i)' % (R,G,B)
                        #~ elif format == 'yuv':
                            #~ colorstring = 'yuv = (%i,%i,%i)' % (Y,U,V)
                        #~ else: #elif format == 'hex':
                            #~ colorstring = 'hex = %s' % hexcolor.upper()
                        #~ self.SetVideoStatusText(addon='%s%s, %s' % (' '*5,xystring, colorstring))
                        xystring = '%s=(%i,%i)' % (_('pos'),x,y)
                        if self.showVideoPixelAvisynth:
                            if 'flipvertical' in self.flip:
                                y = script.AVI.HeightActual - y
                            if 'fliphorizontal' in self.flip:
                                x = script.AVI.WidthActual - x
                            try:
                                avsYUV = script.AVI.GetPixelYUV(x, y)
                                if avsYUV != (-1,-1,-1):
                                    Y,U,V = avsYUV
                                avsRGBA = script.AVI.GetPixelRGBA(x, y)
                                if avsRGBA != (-1,-1,-1,-1):
                                    R,G,B,A = avsRGBA
                            except:
                                pass
                        rgbstring = '%s=(%i,%i,%i)' % (_('rgb'),R,G,B)
                        rgbastring = '%s=(%i,%i,%i,%i)' % (_('rgba'),R,G,B,A)
                        yuvstring = '%s=(%i,%i,%i)' % (_('yuv'),Y,U,V)
                        hexstring = '%s=%s' % (_('hex'),hexcolor.upper())
                        self.SetVideoStatusText(addon=(xystring, hexstring, rgbstring, rgbastring, yuvstring))#'%s%s, %s' % (' '*5,xystring, colorstring))
                    else:
                        self.SetVideoStatusText()
                    #~ if self.separatevideowindow:
                        #~ ctrl = self.frameTextCtrl2
                    #~ else:
                        #~ ctrl = self.frameTextCtrl2
                    #~ ctrl.SetBackgroundColour(rgb)
                    #~ ctrl.Refresh()

    def OnMouseLeaveVideoWindow(self, event):
        #~ if self.FindFocus() == self.videoWindow:
            #~ self.SetVideoStatusText()
        if self.FindFocus() == self.currentScript:
            self.SetScriptStatusText()
        event.Skip()

    def OnLeftUpVideoWindow(self, event):
        videoWindow = self.videoWindow
        if videoWindow.HasCapture():
            videoWindow.ReleaseMouse()
            videoWindow.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))
        event.Skip()

    def OnCropDialogSpinTextChange(self, event=None):
        script = self.currentScript
        # Display actual spin control value (integer only)
        if not event: # SpinCtrl.SetValue() doesn't generate EVT_TEXT in wx2.9 
            spinCtrl = self.cropDialog.ctrls[self.lastcrop]
        else:
            spinCtrl = event.GetEventObject()
            spinCtrl.SetValue(spinCtrl.GetValue())
        # Update the spin control ranges
        w = script.AVI.Width
        h = script.AVI.Height
        for key in self.cropValues.keys():
            self.cropValues[key] = self.cropDialog.ctrls[key].GetValue()
        self.cropDialog.ctrls['left'].SetRange(0, w-self.options['cropminx']-self.cropValues['-right'])
        self.cropDialog.ctrls['-right'].SetRange(0, w-self.options['cropminx']-self.cropValues['left'])
        self.cropDialog.ctrls['top'].SetRange(0, h-self.options['cropminy']-self.cropValues['-bottom'])
        self.cropDialog.ctrls['-bottom'].SetRange(0, h-self.options['cropminy']-self.cropValues['top'])
        # Paint the crop rectangles
        dc = wx.ClientDC(self.videoWindow)
        dc.SetDeviceOrigin(5,5)
        bdc = wx.BufferedDC(dc, wx.Size(w,h))
        self.PaintAVIFrame(bdc, script, self.currentframenum, shift=False)
        #~ self.PaintAVIFrame(dc, script, self.currentframenum)
        self.PaintCropWarnings(spinCtrl)
        self.SetVideoStatusText()

    def OnCropDialogApply(self, event):
        if self.cropDialog.boolInvalidCrop:
            dlg = wx.MessageDialog(self, _('Invalid crop values detected.  Continue?'),
                _('Warning'), wx.YES_NO|wx.CANCEL)
            ID = dlg.ShowModal()
            dlg.Destroy()
            if ID != wx.ID_YES:
                return
        script = self.currentScript
        # Update the script with the crop text
        croptxt = 'Crop(%(left)i, %(top)i, -%(-right)i, -%(-bottom)i)' % self.cropValues
        # Insert the crop based on the selected radio box option
        choice = self.cropDialog.ctrls['choiceInsert'].GetCurrentSelection()
        if choice == 0:
            # Case 1: Insert at end of script
            self.InsertTextAtScriptEnd(croptxt, script)
        elif choice == 1:
            # Case 2: Insert at script cursor
            script.ReplaceSelection(croptxt)
        if choice == 2:
            # Case 3: Copy Crop() to the clipboard
            text_data = wx.TextDataObject(croptxt)
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(text_data)
                wx.TheClipboard.Close()
        # Hide the crop dialog
        self.cropDialog.Hide()
        for key in self.cropValues.keys():
            self.cropValues[key] = 0
        # Show the updated video frame
        self.refreshAVI = True
        self.ShowVideoFrame()

    def OnCropDialogCancel(self, event):
        script = self.currentScript
        for key in self.cropValues.keys():
            self.cropValues[key] = 0
        dc = wx.ClientDC(self.videoWindow)
        self.PaintAVIFrame(dc, script, self.currentframenum)
        self.cropDialog.Hide()
        
    def OnTrimDialogSpinTextChange(self, event):
        spinCtrl = event.GetEventObject() 
        spinCtrl.SetValue(spinCtrl.GetValue())

    def OnTrimDialogApply(self, event):
        insertMode = self.trimDialog.ctrls['choiceInsert'].GetCurrentSelection()
        useDissolve = self.trimDialog.ctrls['useDissolve'].GetValue()
        if useDissolve:
            useDissolve += self.trimDialog.ctrls['dissolveOverlap'].GetValue()
        if not self.InsertSelectionTrims(cutSelected=self.invertSelection,
                                         insertMode=insertMode,
                                         useDissolve=useDissolve):
            wx.MessageBox(_('You must create at least one frame selection first!'), _('Warning'))
            return
        for slider in self.GetVideoSliderList():
            slider.ToggleSelectionMode(0)
        self.trimDialog.Hide()
        if insertMode == 2:
            self.ShowVideoFrame()

    def OnTrimDialogCancel(self, event):
        # Convert selection bookmarks to regular bookmarks
        bookmarks = self.GetBookmarkFrameList()
        for value, bmtype in bookmarks:
            if bmtype != 0:
                if False:
                    self.AddFrameBookmark(value, bmtype=0, toggle=False)
                else:
                    self.DeleteFrameBookmark(value, bmtype)
        for slider in self.GetVideoSliderList():
            slider.ToggleSelectionMode(0)
        self.trimDialog.Hide()
        self.ShowVideoFrame()
        
    # the following 2 func called from wxp.OptionsDialog, not MainFrame
    def OnCustomizeAutoCompList(self, event):
        choices = []
        for keywords in self.avsazdict.values():
            choices += keywords
        choices.sort(key=lambda k: k.lower())
        dlg = wx.Dialog(self, wx.ID_ANY, _('Select autocomplete keywords'), style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        listbox = wx.CheckListBox(dlg, wx.ID_ANY, choices=choices)
        for i in range(len(choices)):
            if choices[i] not in self.options['autocompleteexclusions']:
                listbox.Check(i)
        idAll = wx.NewId()
        idNone = wx.NewId()
        idExclude = wx.NewId()
        def OnContextMenuItem(event):
            id = event.GetId()
            value = True if id == idAll else False
            if id in [idAll, idNone]:
                for i in range(len(choices)):
                    listbox.Check(i, value)
            else:
                for i in range(len(choices)):
                    if '_' not in choices[i]:
                        continue
                    filtername = choices[i].lower()
                    if filtername in self.optionsFilters\
                    and self.optionsFilters[filtername][2] == 2:
                        listbox.Check(i, False)
                    if filtername in self.options['filteroverrides']\
                    and self.options['filteroverrides'][filtername][2] == 2:
                        listbox.Check(i, False)
        def OnContextMenu(event):
            listbox.Bind(wx.EVT_MENU, OnContextMenuItem, id=idAll)
            listbox.Bind(wx.EVT_MENU, OnContextMenuItem, id=idNone)
            listbox.Bind(wx.EVT_MENU, OnContextMenuItem, id=idExclude)
            menu = wx.Menu()
            menu.Append(idAll, _('select all'))
            menu.Append(idNone, _('select none'))
            menu.Append(idExclude, _('exclude long names'))
            listbox.PopupMenu(menu)
            menu.Destroy()
        listbox.Bind(wx.EVT_CONTEXT_MENU, OnContextMenu)
        okay  = wx.Button(dlg, wx.ID_OK, _('OK'))
        cancel = wx.Button(dlg, wx.ID_CANCEL, _('Cancel'))
        btns = wx.StdDialogButtonSizer()
        btns.AddButton(okay)
        btns.AddButton(cancel)
        btns.Realize()
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(listbox, 1, wx.EXPAND|wx.ALL,5)
        sizer.Add(btns, 0, wx.EXPAND|wx.ALL,5)
        dlg.SetSizerAndFit(sizer)
        ID = dlg.ShowModal()
        if ID == wx.ID_OK:
            for i, keyword in enumerate(choices):
                if listbox.IsChecked(i):
                    try:
                        self.options['autocompleteexclusions'].discard(keyword)
                    except KeyError:
                        pass
                else:        
                    self.options['autocompleteexclusions'].add(keyword)
        dlg.Destroy()

    def OnConfigureVideoStatusBarMessage(self, event):
        dlg = wx.Dialog(self, wx.ID_ANY, _('Customize the video status bar message'))
        label = wx.StaticText(dlg, wx.ID_ANY, _('Video status bar message:'))
        textCtrl = wx.TextCtrl(dlg, wx.ID_ANY, self.videoStatusBarInfo.replace('\t','\\t'), size=(500,-1))
        textCtrl.SetSelection(0,0)
        box = wx.StaticBox(dlg, wx.ID_ANY, _('Legend'))
        staticBoxSizer = wx.StaticBoxSizer(box, wx.HORIZONTAL)
        keyList = [
            (
            ('%F', _('Current frame')),
            ('%FC', _('Framecount')),
            ('%T', _('Current time')),
            ('%TT', _('Total time')),
            ('%W', _('Width')),
            ('%H', _('Height')),
            ('%AR', _('Aspect ratio')),
            ('%FR', _('Framerate')),
            ('%FRN', _('Framerate numerator')),
            ('%FRD', _('Framerate denominator')),
            ('%CS', _('Colorspace')),
            ('%FB', _('Field or frame based')),
            ('%P', _('Parity')),
            ('%PS', _('Parity short (BFF or TFF)')),
            ),
            (
            ('%AUR', _('Audio rate')),
            ('%AUL', _('Audio length')),
            ('%AUC', _('Audio channels')),
            ('%AUB', _('Audio bits')),
            ('%AUT', _('Audio type (Integer or Float)')),
            ('%POS', _('Pixel position (cursor based)')),
            ('%HEX', _('Pixel hex color (cursor based)')),
            ('%RGB', _('Pixel rgb color (cursor based)')),
            ('%YUV', _('Pixel yuv color (cursor based)')),
            ('%CLR', _('Pixel color (auto-detect colorspace)')),
            ('%Z', _('Program zoom')),
            ),
        ]
        for eachList in keyList:
            gridSizer = wx.FlexGridSizer(cols=2, hgap=0, vgap=3)
            for key, value in eachList:
                gridSizer.Add(wx.StaticText(dlg, wx.ID_ANY, key), 0, 0)
                gridSizer.Add(wx.StaticText(dlg, wx.ID_ANY, '  -  '+value), 0, 0)
            staticBoxSizer.Add(gridSizer, 0, wx.LEFT|wx.RIGHT, 20)
        noteText = wx.StaticText(dlg, wx.ID_ANY, _('Note: The "\\t\\t" or "\\T\\T" is used to separate the left and right portions of the status bar\n         message.'))
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(label, 0, wx.BOTTOM, 5)
        sizer.Add(textCtrl, 0, wx.EXPAND|wx.BOTTOM, 5)
        sizer.Add(staticBoxSizer, 0, wx.EXPAND|wx.ALL, 5)
        sizer.Add(noteText, 0, wx.ALL, 5)
        # Standard buttons
        okay  = wx.Button(dlg, wx.ID_OK, _('OK'))
        okay.SetDefault()
        okay.SetFocus()
        cancel = wx.Button(dlg, wx.ID_CANCEL, _('Cancel'))
        btns = wx.StdDialogButtonSizer()
        btns.AddButton(okay)
        btns.AddButton(cancel)
        btns.Realize()
        dlgSizer = wx.BoxSizer(wx.VERTICAL)
        dlgSizer.Add(sizer, 0, wx.ALL, 5)
        dlgSizer.Add(btns, 0, wx.EXPAND|wx.ALL, 5)
        dlg.SetSizer(dlgSizer)
        dlg.Fit()
        ID = dlg.ShowModal()
        if ID == wx.ID_OK:
            text = textCtrl.GetValue().replace('\\t', '\t')
            self.options['videostatusbarinfo'] = text
            self.videoStatusBarInfo = text
            self.videoStatusBarInfoParsed, self.showVideoPixelInfo, self.showVideoPixelAvisynth = self.ParseVideoStatusBarInfo(self.videoStatusBarInfo)
        dlg.Destroy()

        #~ if self.options['videostatusbarinfo'] == None:
            #~ self.videoStatusBarInfo = ' ' + _('Frame') + ' %F / %FC  -  (%T)      %POS  %RGB \t\t %Z %Wx%H (%AR)  -  %FR ' + _('fps')
        #~ else:
            #~ self.videoStatusBarInfo = self.options['videostatusbarinfo']
        #~ self.videoStatusBarInfoParsed, self.showVideoPixelInfo = self.ParseVideoStatusBarInfo(self.videoStatusBarInfo)

    def OnScrollUserSlider(self, event):
        pass

    def OnLeftUpUserSlider(self, event):
        slider = event.GetEventObject()
        self.UserSliderVideoUpdate(slider)
        event.Skip()

    def UserSliderVideoUpdate(self, slider):
        script = self.currentScript
        label = slider.GetName()
        sOpen = self.sliderOpenString
        sClose = self.sliderCloseString
        sliderText = None
        for text in self.regexp.findall(script.GetText()):
            if label == text.lstrip(sOpen).rstrip(sClose).split(',')[0].strip('"').strip("'"):
                sliderText = text
                break
        if sliderText:
            pos = script.FindText(0, script.GetTextLength(), sliderText)
            script.SetTargetStart(pos)
            posEnd = script.FindText(pos, script.GetTextLength(), '>]') + 2
            script.SetTargetEnd(posEnd)
            newVal = slider.GetValue()
            items = [s.strip() for s in sliderText.strip('[]').split(',')]
            if len(items) == 4:
                newSliderText = '%s"%s", %s, %s, %s%s' % (sOpen, label, items[1], items[2], newVal, sClose)
            script.ReplaceTarget(newSliderText)
            self.refreshAVI = True
        self.ShowVideoFrame(userScrolling=True)

    def OnToggleTagChecked(self, event):
        script = self.currentScript
        label = event.GetEventObject().GetName()
        if event.IsChecked():
            value = 1
        else:
            value = 0
        # Update the script
        newText = re.sub('\[%s(\s*=.*?)*?\]' % label, '[%s=%i]' % (label, value), script.GetText())
        script.SetText(newText)
        # Update the video
        self.refreshAVI = True
        self.ShowVideoFrame(userScrolling=False)

    def OnSliderLabelToggleAllFolds(self, event):
        script = self.currentScript
        numFolded = 0
        for item in script.sliderToggleLabels:
            if item.GetLabel().startswith('+'):
                numFolded += 1
        if numFolded == 0:
            self.foldAllSliders = True
        if numFolded == len(script.sliderToggleLabels):
            self.foldAllSliders = False
        for item in script.sliderToggleLabels:
            self.ToggleSliderFold(item, fold=self.foldAllSliders, refresh=False)
        script.sliderSizerNew.Layout()
        script.sliderWindow.FitInside()
        script.sliderWindow.Refresh()
        self.foldAllSliders = not self.foldAllSliders

    def OnSliderLabelEditDatabase(self, event):
        ctrl = self.lastContextMenuWin
        name = ctrl.GetLabel().lstrip(' -+').split()[0]
        lowername = name.lower()
        #~ calltip = self.currentScript.FilterNameArgs[name.lower()]
        calltip = self.avsfilterdict[lowername][0]
        dlg = AvsFilterAutoSliderInfo(self, self, name, calltip)
        ID = dlg.ShowModal()
        # Set the data
        if ID == wx.ID_OK:
            newCalltip = dlg.GetNewFilterInfo()
            #~ for key, value in self.optionsFilters.items():
                #~ if key.lower() == name.lower():
                    #~ self.optionsFilters[key] = newCalltip
                    #~ for index in xrange(self.scriptNotebook.GetPageCount()):
                        #~ script = self.scriptNotebook.GetPage(index)
                        #~ script.DefineKeywordCalltipInfo(self.optionsFilters, self.optionsFilterPresets, self.optionsFilterDocpaths, self.optionsFilterTypes, self.optionsKeywordLists)
                    #~ self.ShowVideoFrame(forceRefresh=True)
                    #~ break
            info = self.optionsFilters.get(lowername)
            if info is not None:
                info = self.options['filteroverrides'].get(lowername, info)
                self.options['filteroverrides'][lowername] = (name, newCalltip, info[2])
                self.defineScriptFilterInfo()
                for i in xrange(self.scriptNotebook.GetPageCount()):
                    script = self.scriptNotebook.GetPage(i)
                    script.Colourise(0, script.GetTextLength())
        dlg.Destroy()

    def OnSliderLabelSettings(self, event):
        dlg = wxp.OptionsDialog(self, self.optionsDlgInfo, self.options, startPageIndex=5)
        ID = dlg.ShowModal()
        # Set the data
        if ID == wx.ID_OK:
            self.options = dlg.GetDict()
            self.SetProgramTitle()
        dlg.Destroy()

    def OnSliderLabelModifySliderProperties(self, event):
        ctrl = self.lastContextMenuWin

    def OnContextMenu(self, event):
        win = event.GetEventObject()
        self.lastContextMenuWin = win
        pos = win.ScreenToClient(event.GetPosition())
        try:
            win.PopupMenu(win.contextMenu, pos)
        except AttributeError:
        #except (AttributeError, wx._core.PyAssertionError):
            pass
            #~ print>>sys.stderr, _('Error: no contextMenu variable defined for window')

    def OnScriptTextChange(self, event):
        if event.GetEventObject() == self.FindFocus():
            self.SetScriptStatusText()
        event.Skip()

    def _x_OnScriptSavePointLeft(self, event):
        script = event.GetEventObject()
        if script == self.scriptNotebook.GetCurrentPage():
            index = self.scriptNotebook.GetSelection()
        else:
            for index in xrange(self.scriptNotebook.GetPageCount()):
                if script == self.scriptNotebook.GetPage(index):
                    break
        title = '* %s' % self.scriptNotebook.GetPageText(index).lstrip('* ')
        self.scriptNotebook.SetPageText(index, title)
        self.SetProgramTitle()

    def _x_OnScriptSavePointReached(self, event):
        script = event.GetEventObject()
        if script == self.scriptNotebook.GetCurrentPage():
            index = self.scriptNotebook.GetSelection()
        else:
            for index in xrange(self.scriptNotebook.GetPageCount()):
                if script == self.scriptNotebook.GetPage(index):
                    break
        title = self.scriptNotebook.GetPageText(index).lstrip('* ')
        self.scriptNotebook.SetPageText(index, title)
        self.SetProgramTitle()

    def OnScriptKeyUp(self, event):
        self.AutoUpdateVideo()
        event.Skip()

    def OnFocusScriptWindow(self, event):
        self.SetStatusWidths([-1, 0])
        self.SetScriptStatusText()
        #~ event.GetEventObject().SetCaretWidth(1)
        self.refreshAVI = True
        event.Skip()
        self.UpdateTabImages()

    def OnFocusVideoWindow(self, event):
        self.SetVideoStatusText()
        self.UpdateTabImages()
        #~ event.Skip()

    def OnPaintVideoWindow(self, event):
        dc = wx.PaintDC(self.videoWindow)
        if self.previewWindowVisible:
            script = self.currentScript
            self.PaintAVIFrame(dc, script, self.currentframenum, isPaintEvent=True)
    
    def OnZoomInOut(self, event):
        id = event.GetId()
        vidmenus = [self.videoWindow.contextMenu, self.GetMenuBar().GetMenu(2)]
        for vidmenu in vidmenus:
            menu = vidmenu.FindItemById(vidmenu.FindItem(_('&Zoom'))).GetSubMenu()
            menuItem = menu.FindItemById(id)
            if menuItem:
                label = menuItem.GetLabel()
                break
        for i in range(6):
            menuItem = menu.FindItemByPosition(i)
            if menuItem.IsChecked():
                if label == _('Zoom in') and i < 5:
                    self.OnMenuVideoZoom(None, menu.FindItemByPosition(i+1))
                elif label == _('Zoom out') and i > 0:
                    self.OnMenuVideoZoom(None, menu.FindItemByPosition(i-1))
                break
                
    def OnCharHook(self, event):
        if event.GetKeyCode() != wx.WXK_ESCAPE or not self.useEscape:
            event.Skip()
            return
        shortcut = 'Escape'
        if event.ShiftDown():
            shortcut = 'Shift+' + shortcut
        if event.AltDown():
            shortcut = 'Alt+' + shortcut
        if event.ControlDown():
            shortcut = 'Ctrl+' + shortcut
        IsReserved = shortcut in self.options['reservedshortcuts']
        if IsReserved and self.FindFocus() == self.currentScript\
        and (self.currentScript.AutoCompActive() or self.currentScript.CallTipActive()):
            self.currentScript.CmdKeyExecute(wx.stc.STC_CMD_CANCEL)
        elif IsReserved and self.cropDialog.IsShown():
            self.OnCropDialogCancel(None)
        elif IsReserved and self.trimDialog.IsShown():
            self.OnTrimDialogCancel(None)
        else:
            self.MacroExecuteMenuCommand(shortcut)
                
# Utility functions
    def ExitProgram(self):
        # Don't exit if saving an avi
        try:
            if self.dlgAvs2avi.IsShown():
                return
        except AttributeError:
            pass
        # Save scripts if necessary
        frame = self.GetFrameNumber()
        previewvisible = self.previewWindowVisible
        selected = self.scriptNotebook.GetSelection()
        #~ selected = self.currentScript.filename
        if self.separatevideowindow:
            if self.videoDialog.IsIconized():
                self.videoDialog.Iconize(False)
            self.options['maximized2'] = False
            if self.videoDialog.IsMaximized():
                self.options['maximized2'] = True
                self.videoDialog.Maximize(False)
        self.HidePreviewWindow()
        if self.IsIconized():
            self.Iconize(False)
        if self.cropDialog.IsShown():
            self.OnCropDialogCancel(None)
        if self.trimDialog.IsShown():
            self.OnTrimDialogCancel(None)
        if self.options['promptexitsave']:
            for index in xrange(self.scriptNotebook.GetPageCount()):
                script = self.scriptNotebook.GetPage(index)
                tabTitle = self.scriptNotebook.GetPageText(index)
                if script.GetModify():
                    self.scriptNotebook.SetSelection(index)
                    dlg = wx.MessageDialog(self, _('Save changes before closing?'),
                        tabTitle, wx.YES_NO|wx.CANCEL)
                    ID = dlg.ShowModal()
                    dlg.Destroy()
                    if ID == wx.ID_YES:
                        self.SaveScript(script.filename, index)
                    elif ID == wx.ID_CANCEL:
                        return
        # Save the session
        if self.options['startupsession']:
            self.SaveSession(self.lastSessionFilename, saverecentdir=False,
                frame=frame,
                previewvisible=previewvisible,
                selected=selected,
            )
        # Save the text in the scrap window
        scrapCtrl = self.scrapWindow.textCtrl
        self.options['scraptext'] = (scrapCtrl.GetText(), scrapCtrl.GetAnchor(), scrapCtrl.GetCurrentPos())
        # Save the zoom factor
        vidmenu = self.videoWindow.contextMenu
        menu = vidmenu.FindItemById(vidmenu.FindItem(_('&Zoom'))).GetSubMenu()
        for i, menuItem in enumerate(menu.GetMenuItems()):
            if menuItem.IsChecked():
                self.options['zoomindex'] = i
                break
        # Save the program position
        self.options['maximized'] = False
        if self.IsMaximized():
            self.options['maximized'] = True
            self.Maximize(False)
        x, y, w, h = self.GetRect()
        #~ display = wx.Display(wx.Display.GetFromWindow(self))
        #~ xoffset, yoffset = display.GetGeometry().GetPosition()
        #~ self.options['dimensions'] = (x + xoffset, y + yoffset, w, h)
        self.options['dimensions'] = (max(x,20), max(y,20), w, h)
        if self.separatevideowindow:
            x, y, w, h = self.videoDialog.GetRect()
            #~ display = wx.Display(wx.Display.GetFromWindow(self.videoDialog))
            #~ xoffset, yoffset = display.GetGeometry().GetPosition()
            #~ self.options['dimensions2'] = (x + xoffset, y + yoffset, w, h)
            self.options['dimensions2'] = (x, y, w, h)
        # Save the crop choice
        self.options['cropchoice'] = self.cropDialog.ctrls['choiceInsert'].GetCurrentSelection()
        # Save the trim options
        self.options['triminsertchoice'] = self.trimDialog.ctrls['choiceInsert'].GetCurrentSelection()
        self.options['trimmarkframes'] = self.markFrameInOut
        if self.invertSelection:
            self.options['trimreversechoice'] = 1
        else:
            self.options['trimreversechoice'] = 0
        # Save the persistent options
        self.options['exitstatus'] = 0
        f = open(self.optionsfilename, mode='wb')
        cPickle.dump(self.options, f, protocol=0)
        f.close()
        # Clean up
        wx.TheClipboard.Flush()
        for index in xrange(self.scriptNotebook.GetPageCount()):
            script = self.scriptNotebook.GetPage(index)
            script.AVI = None
        pyavs.ExitRoutines()
        if self.boolSingleInstance:
            self.argsPosterThread.Stop()
        self.Destroy()

    def NewTab(self, copyselected=True, select=True, splits=None):
        if self.cropDialog.IsShown():
            wx.MessageBox(_('Cannot create a new tab while crop editor is open!'), 
                          _('Error'), style=wx.OK|wx.ICON_ERROR)
            return False
        if self.trimDialog.IsShown():
            wx.MessageBox(_('Cannot create a new tab while trim editor is open!'), 
                          _('Error'), style=wx.OK|wx.ICON_ERROR)
            return False
        self.Freeze()
        # Store the current selected text
        oldselected = self.currentScript.GetSelectedText()
        # Create a new script window instance
        scriptWindow = self.createScriptWindow()
        self.currentScript = scriptWindow
        # Determine the name of the tab (New File (x))
        index = self.scriptNotebook.GetPageCount()
        if self.options['multilinetab']:
            rows = self.scriptNotebook.GetRowCount()
        iMax = 0
        for i in range(index):
            title = self.scriptNotebook.GetPageText(i).lstrip('* ')
            if title.startswith('%s (' % self.NewFileName) and title.endswith(')'):
                iNewFile = 0
                strNum = title.split('%s (' % self.NewFileName)[1].rstrip(')')
                try:
                    iNewFile = int(strNum)
                except ValueError:
                    iNewFile = 100
                if iNewFile>iMax:
                    iMax = iNewFile
        # Add the tab to the notebook
        # Paste the old selected text (unless it only contains whitespace)
        if copyselected and oldselected.strip():
            self.scriptNotebook.AddPage(scriptWindow,'%s (%s)' % (self.NewFileName, iMax+1), select=False)
            scriptWindow.SetText(oldselected)
            scriptWindow.SelectAll()
            self.refreshAVI = True
            if select:
                self.scriptNotebook.SetSelection(self.scriptNotebook.GetPageCount()-1)
        else:
            if select:
                self.HidePreviewWindow()
            self.scriptNotebook.AddPage(scriptWindow,'%s (%s)' % (self.NewFileName, iMax+1), select=select)
        scriptWindow.SetFocus()
        self.UpdateTabImages()
        scriptWindow.EnsureCaretVisible()
        # a workaroud for multiline notebook issue
        if self.options['multilinetab']:
            if rows != self.scriptNotebook.GetRowCount():
                w, h = self.scriptNotebook.GetSize()
                self.scriptNotebook.SetSize((w, h-1))
                self.scriptNotebook.SetSize((w, h))
        self.Thaw()

    def OpenFile(self, filename='', scripttext=None, setSavePoint=True, splits=None, framenum=None):#, index=None):
        # Get filename via dialog box if not specified
        if not filename:
            #~ filefilter = _('AviSynth script (*.avs, *.avsi)|*.avs;*.avsi|All files (*.*)|*.*')
            extlist = self.options['templates'].keys()
            extlist.sort()
            extlist2 = [s for s in extlist if not s.startswith('avs')]
            extlist1 = ', '.join(extlist2)
            extlist2 = ';*.'.join(extlist2)
            filefilter = _('AviSynth script (avs, avsi)|*.avs;*.avsi|Source files (%(extlist1)s)|*.%(extlist2)s|All files (*.*)|*.*') %  locals()
            dlg = wx.FileDialog(self,_('Open a script or source'),
                self.options['recentdir'], '', filefilter, wx.OPEN|wx.MULTIPLE)
            ID = dlg.ShowModal()
            if ID == wx.ID_OK:
                filenames = dlg.GetPaths()
                if len(filenames) == 1:
                    filename = filenames[0]
                else:
                    for filename in filenames:
                        if filename:
                            self.OpenFile(filename, scripttext, setSavePoint, splits, framenum)
                    return
            dlg.Destroy()
        # Open script if filename exists (user could cancel dialog box...)
        if filename:
            # If script already exists in a tab, select that tab and exit
            for index in xrange(self.scriptNotebook.GetPageCount()):
                script = self.scriptNotebook.GetPage(index)
                if filename == script.filename:
                    self.SelectTab(index)
                    if script.GetModify():
                        dlg = wx.MessageDialog(self, _('Reload the file and lose the current changes?'),
                            os.path.basename(filename), wx.YES_NO)
                        ID = dlg.ShowModal()
                        dlg.Destroy()
                        if ID == wx.ID_YES:
                            txt = self.GetMarkedScriptFromFile(filename)
                            script.SetText(txt)
                            if setSavePoint:
                                script.EmptyUndoBuffer()
                                script.SetSavePoint()
                            self.refreshAVI = True
                            if self.previewWindowVisible:
                                self.ShowVideoFrame()
                    dirname = os.path.dirname(filename)
                    if os.path.isdir(dirname):
                        self.options['recentdir'] = dirname
                    return
            # Get current tab if not specified
            if True: #index is None:
                # Make a new tab if current one is not empty
                indexCur = self.scriptNotebook.GetSelection()
                txt = self.scriptNotebook.GetPage(indexCur).GetText()
                title = self.scriptNotebook.GetPageText(indexCur)
                if txt == "" and title.startswith(self.NewFileName):
                    boolNewTab = False
                    index = indexCur
                else:
                    boolNewTab = True
                    self.NewTab(splits=splits)
                    index = self.scriptNotebook.GetSelection()
            script = self.scriptNotebook.GetPage(index)
            if splits is not None:
                script.lastSplitVideoPos = splits[0]
                script.lastSplitSliderPos = splits[1]
                script.sliderWindowShown = splits[2]
            script.lastFramenum = framenum
            # Process the filename
            dirname, basename = os.path.split(filename)
            root, ext = os.path.splitext(basename)
            if ext.lower() == '.ses':
                self.LoadSession(filename)
            elif ext.lower() not in ('.avs', '.avsi'):
                # Treat the file as a source
                self.InsertSource(filename)
                if self.previewWindowVisible:
                    self.ShowVideoFrame()
            else:
                if dirname != '':
                    self.scriptNotebook.SetPageText(index, basename)
                    self.SetProgramTitle()
                    script.filename = filename
                elif not root.startswith(self.NewFileName):
                    self.scriptNotebook.SetPageText(index, root)
                    self.SetProgramTitle()
                # Treat the file as an avisynth script
                if scripttext is None:
                    txt = self.GetMarkedScriptFromFile(filename)
                    script.SetText(txt)
                else:
                    script.SetText(scripttext)
                if setSavePoint:
                    script.EmptyUndoBuffer()
                    script.SetSavePoint()
                self.refreshAVI = True
                if self.previewWindowVisible:
                    self.ShowVideoFrame()
                self.UpdateRecentFilesList(filename)
            # Misc stuff
            if os.path.isdir(dirname):
                self.options['recentdir'] = dirname

    def GetMarkedScriptFromFile(self, filename, returnFull=False):
        try:
            f = open(filename, 'r')
            txt = f.read()
            f.close()
        except UnicodeDecodeError:
            f = codecs.open(filename, 'rU', encoding)
            txt = f.read()
            f.close()
        #~ f = codecs.open(filename, 'rU', encoding)
        #~ txt = f.read()
        #~ f.close()
        
        lines = txt.rstrip().split('\n')
        lines.reverse()
        header = '### AvsP marked script ###'
        if lines[0] == header:
            newlines = []
            for line in lines[1:]:
                if line == header:
                    break
                if line.startswith('# '):
                    newlines.append(line[2:])
                else:
                    if returnFull:
                        return txt, txt
                    else:
                        return txt
            newlines.reverse()
            if returnFull:
                return '\n'.join(newlines), txt
            else:
                return '\n'.join(newlines)
        else:
            if returnFull:
                return txt, txt
            else:
                return txt

    def UpdateRecentFilesList(self, filename=None):
        # Update the persistent internal list
        if filename is not None:
            if type(filename) != unicode:
                filename = unicode(filename, encoding)
            # Add the filename to the internal list
            if not os.path.isfile(filename):
                return
            if self.options['recentfiles'] is None:
                self.options['recentfiles'] = []

            #~ try:
                #~ if filename in self.options['recentfiles']:
                    #~ return
            #~ except UnicodeDecodeError:
                #~ if unicode(filename, encoding) in self.options['recentfiles']:
                    #~ return
            if filename in self.options['recentfiles']:
                return

            self.options['recentfiles'].insert(0, filename)
            n1 = len(self.options['recentfiles'])
            n2 = self.options['nrecentfiles']
            if n1 > n2:
                self.options['recentfiles'] = self.options['recentfiles'][:n2]
            nameList = [filename]
        else:
            if self.options['recentfiles'] is None:
                return
            nameList = self.options['recentfiles'][::-1]
        # Find the menu position
        menu = self.GetMenuBar().GetMenu(0)
        nMenuItems = menu.GetMenuItemCount()
        i = nMenuItems - 1 - 2
        while i >= 0:
            menuItem = menu.FindItemByPosition(i)
            if menuItem.IsSeparator():
                break
            i -= 1
        if i == 0:
            return
        # Insert the new menu items
        pos = i + 1
        for name in nameList:
            if len(name) > 43:
                label = name[:15] + '...' + name[-25:]
            else:
                label = name
            newMenuItem = menu.Insert(pos, wx.ID_ANY, label, _("Open this file"))
            self.Bind(wx.EVT_MENU, self.OnMenuFileRecentFile, newMenuItem)
        # Delete extra menu items
        nMenuItems = menu.GetMenuItemCount()
        nNameItems = (nMenuItems - 1 - 2) - pos + 1
        nMax = self.options['nrecentfiles']
        if nNameItems > nMax:
            pos += nMax
            for i in range(nNameItems-nMax):
                badMenuItem = menu.FindItemByPosition(pos)
                menu.Delete(badMenuItem.GetId())

    def CloseTab(self, index=None, boolPrompt=False):
        # Get the script and corresponding index
        script, index = self.getScriptAtIndex(index)
        if script is None:
            return False
        # Prompt user to save changes if necessary
        if boolPrompt:
            tabTitle = self.scriptNotebook.GetPageText(index)
            if script.GetModify():
                #~ self.HidePreviewWindow()
                self.scriptNotebook.SetSelection(index)
                dlg = wx.MessageDialog(self, _('Save changes before closing?'),
                    tabTitle, wx.YES_NO|wx.CANCEL)
                ID = dlg.ShowModal()
                dlg.Destroy()
                if ID == wx.ID_YES:
                    self.SaveScript(script.filename, index)
                elif ID == wx.ID_CANCEL:
                    return False
        else:
            if script.filename:
                self.SaveScript(script.filename, index)
        # Delete the tab from the notebook
        boolSelected = (index == self.scriptNotebook.GetSelection())
        script.AVI = None #self.scriptNotebook.GetPage(index).AVI = None # clear memory
        # If only 1 tab, make another
        if self.scriptNotebook.GetPageCount() == 1:
            self.NewTab(copyselected=False)
            self.scriptNotebook.SetPageText(1, self.NewFileName)
            self.SetProgramTitle()
            self.HidePreviewWindow()
        if self.options['multilinetab']:
            rows = self.scriptNotebook.GetRowCount()
        self.scriptNotebook.DeletePage(index)
        if boolSelected:
            if index==0:
                newIndex = 0
            else:
                newIndex = index-1
            self.scriptNotebook.SetSelection(newIndex)
        self.UpdateTabImages()
        if self.options['multilinetab']:
            if rows != self.scriptNotebook.GetRowCount():
                w, h = self.scriptNotebook.GetSize()
                self.scriptNotebook.SetSize((w, h-1))
                self.scriptNotebook.SetSize((w, h))
        return True

    def CloseAllTabs(self):
        dlg = wx.MessageDialog(self, _('Save session before closing all tabs?'),
            _('Warning'), wx.YES_NO|wx.CANCEL)
        ID = dlg.ShowModal()
        dlg.Destroy()
        if ID == wx.ID_CANCEL:
            return
        if ID == wx.ID_YES:
            if not self.SaveSession():
                return
        for index in xrange(self.scriptNotebook.GetPageCount()):
            self.CloseTab(0)
    

    def SaveScript(self, filename='', index=None):
        script, index = self.getScriptAtIndex(index)
        if script is None:
            return None
        # Get filename via dialog box if not specified
        if not filename or not (filename.endswith('.avs') or filename.endswith('.avsi')):            
            filefilter = _('AviSynth script (*.avs, *.avsi)|*.avs;*.avsi|All files (*.*)|*.*')
            initialdir = None
            initialname = self.scriptNotebook.GetPageText(index).lstrip('* ')
            if script.filename:
                initialdir = script.filename
            else:
                stringList = [s.strip('"') for s in re.findall('".+?"', script.GetText())]
                #~ extList = ['.%s' % s for s in self.options['templates'].keys()]
                sourceFilterList = [s.split('(')[0].strip().lower() for s in self.options['templates'].values()]
                sourceFilterList.append('directshowsource')
                findpos = -1
                lastpos = script.GetLength()
                for s in stringList:
                    if os.path.isfile(s) and os.path.splitext(s)[1].lower() not in ('.dll', '.avs'):
                        findpos = script.FindText(findpos+1, lastpos, s)
                        openpos = script.GetOpenParenthesesPos(findpos)
                        if openpos is not None:
                            wordstartpos = script.WordStartPosition(openpos,1)
                            if wordstartpos != -1:
                                sourceFilter = script.GetTextRange(wordstartpos, openpos)
                                if sourceFilter.lower() in sourceFilterList:
                                    initaldir, initialname = os.path.split(s)
                                    initialname = '%s.avs' % os.path.splitext(initialname)[0]
                                    break
                if initialdir is None:
                    initialdir = self.options['recentdir']
            dlg = wx.FileDialog(self,_('Save current script'),
                initialdir, initialname, filefilter, wx.SAVE | wx.OVERWRITE_PROMPT)
            ID = dlg.ShowModal()
            if ID == wx.ID_OK:
                filename = dlg.GetPath()
            dlg.Destroy()
        # Save script if filename exists (either given or user clicked OK)
        if filename:
            # Process the filename
            dirname, basename = os.path.split(filename)
            root, ext = os.path.splitext(basename)
            if not os.path.isdir(dirname):
                wx.MessageBox(_('Directory %(dirname)s does not exist!') % locals(), _('Error'), style=wx.OK|wx.ICON_ERROR)
                return None
            if ext.lower() not in ('.avs', '.avsi'):
                basename = root+'.avs'
            if os.path.splitext(script.filename)[1].lower() == '.avsi':
                basename = root+'.avsi'
            filename = os.path.join(dirname, basename)
            # Save the text to the specified file
            #~ txt = self.regexp.sub(self.re_replace, script.GetText())
            scriptText = script.GetText()
            txt = self.getCleanText(scriptText)
            if txt != scriptText and self.options['savemarkedavs']:
                header = '### AvsP marked script ###'
                base = '\n'.join(['# %s' % line for line in scriptText.split('\n')])
                txt = '%(txt)s\n%(header)s\n%(base)s\n%(header)s' % locals()
            try:
                f = open(filename, 'w')
                f.write(txt)
                f.close()
            except UnicodeEncodeError:
                #~ f = codecs.open(filename, 'w', encoding)
                f.write(txt.encode(encoding))
                f.close()
            #~ script.SaveFile(filename)
            script.SetSavePoint()
            # Misc stuff
            script.filename = filename
            self.scriptNotebook.SetPageText(index, basename)
            self.SetProgramTitle()
            if os.path.isdir(dirname):
                self.options['recentdir'] = dirname
            self.refreshAVI = True
            #~ script.previewtxt = None
            self.UpdateRecentFilesList(filename)
        else:
            return None
        return filename

    def getScriptAtIndex(self, index):
        if index is None:
            script = self.currentScript
            index = self.scriptNotebook.GetSelection()
        else:
            try:
                index = int(index)
                if index < 0:
                    return None, None
                if index >= self.scriptNotebook.GetPageCount():
                    return None, None
                script = self.scriptNotebook.GetPage(index)
            except TypeError:
                return None, None
            except ValueError:
                return None, None
        return script, index

    def getCleanText(self, text):
        text = self.cleanSliders(text)
        text = self.cleanToggleTags(text)
        return text
        

    def CopyTextToNewTab(self, index=None):
        script, index = self.getScriptAtIndex(index)
        text = script.GetText()
        self.NewTab(copyselected=False, select=False)
        self.currentScript.SetText(text)
        self.currentScript.SelectAll()
        self.refreshAVI = True
        self.scriptNotebook.SetSelection(self.scriptNotebook.GetPageCount()-1)
        
    def RepositionTab(self, newIndex):
        if type(newIndex) is not int:        
            id = newIndex.GetId()
            menu = self.scriptNotebook.contextMenu
            menuItem = menu.FindItemByPosition(menu.GetMenuItemCount()-1)
            menu = menuItem.GetSubMenu()
            for newIndex in range(menu.GetMenuItemCount()):
                if id == menu.FindItemByPosition(newIndex).GetId():
                    break        
        index = self.scriptNotebook.GetSelection()
        page = self.scriptNotebook.GetPage(index)
        label = self.scriptNotebook.GetPageText(index)
        win = self.FindFocus()
        if newIndex < index:
            self.scriptNotebook.InsertPage(newIndex, page, label)
            self.scriptNotebook.ChangeSelection(newIndex)
            self.scriptNotebook.RemovePage(index+1)
        else:
            self.scriptNotebook.InsertPage(newIndex+1, page, label)
            self.scriptNotebook.ChangeSelection(newIndex+1)
            self.scriptNotebook.RemovePage(index)
        if win:
            win.SetFocus()
        self.UpdateTabImages()

    def cleanSliders(self, text):
        return self.regexp.sub(self.re_replace, text)

    def cleanToggleTags(self, text):
        for endtag in re.findall('\[/.*?\]', text):
            tagname = endtag[2:-1]
            expr = re.compile('\[%s(\s*=.*?)*?\].*?\[/%s\]' % (tagname, tagname), re.IGNORECASE|re.DOTALL)
            text = expr.sub(self.re_replace2, text)
        return text

    def LoadSession(self, filename=None, saverecentdir=True, resize=True, backup=False, startup=False):
        # Get the filename to load from the user
        if filename is None or not os.path.isfile(filename):
            filefilter = 'Session (*.ses)|*.ses'
            initialdir = self.options['recentdirSession']
            if not os.path.isdir(initialdir):
                initialdir = self.programdir
            dlg = wx.FileDialog(self,_('Load a session'),
                initialdir, '', filefilter, wx.OPEN)
            ID = dlg.ShowModal()
            if ID == wx.ID_OK:
                filename = dlg.GetPath()
            dlg.Destroy()
        if filename is not None:
            # Load the session info from filename
            f = open(filename, mode='rb')
            session = cPickle.load(f)
            f.close()            
            if self.options['hidepreview'] or self.options['paranoiamode'] or (startup and self.options['exitstatus']):
                previewWindowVisible = False
            else:
                previewWindowVisible = session['previewWindowVisible']
            if backup:
                session['previewWindowVisible'] = False
                f = open(filename, mode='wb')
                cPickle.dump(session, f, protocol=0)
                f.close()
            # Load the text into the tabs
            selectedIndex = None
            self.SelectTab(self.scriptNotebook.GetPageCount() - 1)
            #~ for scriptname, boolSelected, scripttext in session['scripts']:
            self.reloadList = []
            for index, item in enumerate(session['scripts']):
                nItems = len(item)
                defaults = (None, None, None, None, None, 0)
                scriptname, boolSelected, scripttext, crc, splits, framenum = item + defaults[nItems:]
                #~ if len(item) == 4:
                    #~ scriptname, boolSelected, scripttext, crc = item
                #~ else:
                    #~ scriptname, boolSelected, scripttext = item
                    #~ crc = None
                dirname, basename = os.path.split(scriptname)
                setSavePoint = False
                if not os.path.isdir(dirname):
                    if basename:
                        scriptname = '%s.avs' % basename
                    else:
                        scriptname = '%s.avs' % self.NewFileName
                else:
                    if os.path.isfile(scriptname):
                        txt, txtFromFile = self.GetMarkedScriptFromFile(scriptname, returnFull=True)
                        #~ if txt == self.getCleanText(scripttext):
                        try:
                            if txt == scripttext.encode(encoding):
                                setSavePoint = True
                            else:
                                setSavePoint = False
                        except UnicodeEncodeError:
                            setSavePoint = False
                        if crc is not None:
                            try:
                                crc2 = md5.new(txtFromFile).digest()
                            except UnicodeEncodeError:
                                crc2 = md5.new(txtFromFile.encode(encoding)).digest()
                            if crc != crc2:
                                self.reloadList.append((index, scriptname, txt))
                self.OpenFile(filename=scriptname, scripttext=scripttext, setSavePoint=setSavePoint, splits=splits, framenum=framenum)
                if boolSelected:
                    selectedIndex = self.scriptNotebook.GetSelection()
            # Prompt to reload modified files
            if not startup:
                self.ReloadModifiedScripts()
            # Select the last selected script
            if selectedIndex is not None:
                self.scriptNotebook.SetSelection(selectedIndex)
            # Set the video slider to last shown frame number
            if startup:
                self.previewWindowVisible = previewWindowVisible
                self.startupframe = session['frame']
            else:
                if not previewWindowVisible:
                    self.HidePreviewWindow()
                else:
                    self.ShowVideoFrame(session['frame'], resize=resize)

            # Set the bookmarks
            if 'bookmarks' in session:
                if startup:
                    if self.options['loadstartupbookmarks']:
                        self.SetBookmarkFrameList(session['bookmarks'])
                else:
                    self.SetBookmarkFrameList(session['bookmarks'])
                if 'bookmarkDict' in session:
                    self.bookmarkDict.update(session['bookmarkDict'].items())
            # Save the recent dir
            if saverecentdir:
                dirname = os.path.dirname(filename)
                if os.path.isdir(dirname):
                    self.options['recentdirSession'] = dirname

    def ReloadModifiedScripts(self):
        if self.reloadList is not None:
            for index, filename, text in self.reloadList:
                self.scriptNotebook.SetSelection(index)
                dlg = wx.MessageDialog(self, _('File has been modified since the session was saved. Reload?'),
                    os.path.basename(filename), wx.YES_NO|wx.CANCEL)
                ID = dlg.ShowModal()
                dlg.Destroy()
                if ID == wx.ID_YES:
                    script = self.currentScript
                    script.SetText(text)
                    script.SetSavePoint()

    def SaveSession(self, filename=None, saverecentdir=True, frame=None, previewvisible=None, selected=None):
        # Get the filename to save from the user
        if filename is None:
            filefilter = 'Session (*.ses)|*.ses'
            initialdir = self.options['recentdirSession']
            if not os.path.isdir(initialdir):
                initialdir = self.programdir
            dlg = wx.FileDialog(self,_('Save the session'),
                initialdir, '', filefilter, wx.SAVE | wx.OVERWRITE_PROMPT)
            ID = dlg.ShowModal()
            if ID == wx.ID_OK:
                filename = dlg.GetPath()
            dlg.Destroy()
        if filename is not None:
            # Get the text from each script
            scripts = []
            selectedIndex = self.scriptNotebook.GetSelection()
            if selected is not None:
                selectedIndex = selected
            for index in xrange(self.scriptNotebook.GetPageCount()):
                script = self.scriptNotebook.GetPage(index)
                boolSelected = index == selectedIndex
                scriptname = script.filename
                if not os.path.isfile(scriptname):
                    crc = None
                    title = self.scriptNotebook.GetPageText(index).lstrip('* ')
                    if not title.startswith(self.NewFileName):
                        scriptname = title
                else:
                    try:
                        f = open(scriptname, 'r')
                        txt = f.read()
                        f.close()
                        crc = md5.new(txt).digest()
                    except UnicodeDecodeError:
                        f = codecs.open(scriptname, 'rU', encoding)
                        txt = f.read()
                        f.close()
                    #~ f = codecs.open(scriptname, 'rU', encoding)
                    #~ txt = f.read()
                    #~ f.close()
                        crc = md5.new(txt.encode(encoding)).digest()
                splits = (script.lastSplitVideoPos, script.lastSplitSliderPos, script.sliderWindowShown)
                scripts.append((scriptname, boolSelected, script.GetText(), crc, splits, script.lastFramenum))
            # Get the remaining session information, store in a dict
            session = {}
            if frame is None:
                session['frame'] = self.GetFrameNumber()
            else:
                session['frame'] = frame
            if previewvisible is None:
                session['previewWindowVisible'] = self.previewWindowVisible
            else:
                session['previewWindowVisible'] = previewvisible
            session['scripts'] = scripts
            session['bookmarks'] = self.GetBookmarkFrameList()
            session['bookmarkDict'] = self.bookmarkDict
            # Save info to filename
            f = open(filename, mode='wb')
            cPickle.dump(session, f, protocol=0)
            f.close()
            # Save the recent dir
            if saverecentdir:
                dirname = os.path.dirname(filename)
                if os.path.isdir(dirname):
                    self.options['recentdirSession'] = dirname
            return True

    def SaveCurrentImage(self, filename='', index=None):
        extlist = self.imageFormats.keys()
        extlist.sort()
        if not filename:
            #~ extlist1 = ', '.join(extlist)
            #~ extlist2 = ';*'.join(extlist)
            #~ filefilter = _('Source files (%(extlist1)s)|*.%(extlist2)s|All files (*.*)|*.*') %  locals()
            filefilterList = []
            for ext in extlist:
                filefilterList.append('%s|*%s' % (self.imageFormats[ext][0], ext))
            maxFilterIndex = len(filefilterList) - 1
            #~ filefilter = _('Image files (%(extlist1)s)|*%(extlist2)s') %  locals()
            filefilter = '|'.join(filefilterList)
            defaultdir = self.options['imagesavedir']
            if self.options['imagenameformat'].startswith('%s'):
                if not index:
                    index = self.scriptNotebook.GetSelection()
                defaultname = os.path.splitext(self.scriptNotebook.GetPageText(index))[0]
                defaultname = self.options['imagenameformat'] % (defaultname, self.currentframenum)
            else:
                defaultname = self.options['imagenameformat'] % self.currentframenum
            dlg = wx.FileDialog(self,_('Save current frame'), defaultdir, defaultname,
                filefilter,wx.SAVE | wx.OVERWRITE_PROMPT,(0,0))
            dlg.SetFilterIndex(min(self.options['imagechoice'], maxFilterIndex))
            ID = dlg.ShowModal()
            if ID == wx.ID_OK:
                filename = dlg.GetPath()
                prifix = os.path.splitext(os.path.basename(filename))[0]
                self.options['imagechoice'] = dlg.GetFilterIndex()
                self.options['imagesavedir'] = os.path.dirname(filename)
                if prifix.isdigit():
                    self.options['imagenameformat'] = '%d'
                else:
                    self.options['imagenameformat'] = '%s%06d'
            dlg.Destroy()
        if filename:
            script, index = self.getScriptAtIndex(index)
            if script is None or script.AVI is None:
                wx.MessageBox(_('No image to save'), _('Error'), style=wx.OK|wx.ICON_ERROR)
                return False
            #~ if script==None:
                #~ script = self.currentScript
            w = script.AVI.Width
            h = script.AVI.Height
            bmp = wx.EmptyBitmap(w, h)
            mdc = wx.MemoryDC()
            mdc.SelectObject(bmp)
            script.AVI.DrawFrame(self.currentframenum, mdc.GetHDC())
            ext = os.path.splitext(filename)[1].lower()
            if ext not in extlist:
                ext = '.bmp'
                filename = '%s%s' % (filename, ext)
            #~ bmp.SaveFile(filename, self.imageFormats[ext][1])
            img = bmp.ConvertToImage()
            if ext==".jpg":
                quality = self.MacroGetTextEntry("JPEG Quality (0-100)", "70", "JPEG Quality")
                if quality == "":
                    quality = "70"
                try:
                    if int(quality) > 100:
                        quality = "100"
                    if int(quality) < 0:
                        quality = "0"
                except ValueError:
                    quality = "70"
                img.SetOption(wx.IMAGE_OPTION_QUALITY, quality)
            img.SaveFile(filename, self.imageFormats[ext][1])
        else:
            return False
        return True

    #~ def ZoomPreviewWindow(self, zoomfactor, show=True):
        #~ self.zoomfactor = zoomfactor
        #~ if show:
            #~ self.ShowVideoFrame(forceRefresh=True)
            #self.videoWindow.Refresh()

    def InsertText(self, txt, pos=-1, index=None):
        # Get the desired script
        if index == -1:
            script = self.scrapWindow.textCtrl
        else:
            script, index = self.getScriptAtIndex(index)
            if script is None:
                return False
        # Insert the text based on the input pos
        #~ try:
            #~ txt = str(txt)
        #~ except UnicodeEncodeError:
            #~ txt = unicode(txt, encoding)
        if type(txt) != unicode:
            txt = unicode(txt, encoding)
        if pos is None:
            script.ReplaceSelection(txt)
            return True
        elif type(pos) == type(0):
            if pos == -2:
                self.InsertTextAtScriptEnd(txt, script)
                return True
            if pos == -1 or pos > script.GetLength():
                pos = script.GetLength()
            if pos < 0:
                pos = 0
            scriptpos = pos
        elif type(pos) == type((0,0)):
            if len(pos) != 2:
                return False
            line, col = pos
            try:
                line = int(line)
                col = int(col)
            except ValueError:
                return False
            if line == - 1 or line >= script.GetLineCount():
                line = script.GetLineCount() - 1
            if line < 0:
                line = 0
            linepos = script.PositionFromLine(line)
            maxCol = script.GetLineEndPosition(line) - linepos
            if col == -1 or col > maxCol:
                col = maxCol
            if col < 0:
                col = 0
            scriptpos = linepos + col
        script.InsertText(scriptpos, txt)
        script.GotoPos(scriptpos + len(txt))
        return True

    def AutoUpdateVideo(self, force=False):
        script = self.currentScript
        newlinenum = script.LineFromPosition(script.GetCurrentPos())
        if self.options['autoupdatevideo']:
            marker = '__END__'
            pos = script.FindText(0, script.GetTextLength(), marker+'$', stc.STC_FIND_REGEXP)
            if pos != -1:
                line = script.LineFromPosition(pos)
                if newlinenum != line:
                    script.SetTargetStart(pos)
                    script.SetTargetEnd(script.GetLineEndPosition(line))
                    script.ReplaceTarget('')
                    pos = script.GetLineEndPosition(newlinenum)
                    script.InsertText(pos, marker)
            if self.oldlinenum is None:
                pass
            elif newlinenum != self.oldlinenum or force:
                script.OnUpdateUI(None)
                self.refreshAVI = True
                self.IdleCall.append((self.ShowVideoFrame, tuple(), dict(focus=False)))
        self.oldlinenum = newlinenum

    def InsertSource(self, filename=''):
        script = self.currentScript
        strsource, filename = self.GetSourceString(filename, return_filename=True)
        if script.GetText() == '' and filename is not None and os.path.splitext(filename)[1].lower() in ('.avs', '.avsi'):
            self.OpenFile(filename)
        else:
            if strsource != '':
                script.ReplaceSelection('%s\n' % strsource)
                script.SetFocus()
                self.AutoUpdateVideo()
                if self.FindFocus() == self.videoWindow:
                    self.refreshAVI = True
                    self.ShowVideoFrame()

    def GetSourceString(self, filename='', return_filename=False):
        extlist = self.options['templates'].keys()
        extlist.sort()
        if not filename or not os.path.isfile(filename):
            extlist1 = ', '.join(extlist)
            extlist2 = ';*.'.join(extlist)
            filefilter = _('Source files (%(extlist1)s)|*.%(extlist2)s|All files (*.*)|*.*') %  locals()
            recentdir = self.options['recentdir']
            dlg = wx.FileDialog(self, _('Insert a source'), recentdir, '', filefilter, wx.OPEN)
            ID = dlg.ShowModal()
            if ID == wx.ID_OK:
                filename = dlg.GetPath()
            else:
                filename = None
            dlg.Destroy()
        if filename is not None:
            dirname = os.path.dirname(filename)
            if os.path.isdir(dirname):
                self.options['recentdir'] = dirname
            ext = os.path.splitext(filename)[1][1:].lower()
            strsource = self.options['templates'].get(ext, u'DirectShowSource(***)')
            # TODO: fix unicode bug here?
            strsource = strsource.replace(u'[***]', u'"%s"' % os.path.basename(filename))
            strsource = strsource.replace(u'***', u'"%s"' % filename)
        else:
            strsource = ''
        if return_filename:
            return (strsource, filename)
        else:
            return strsource

    def InsertPlugin(self, filename=''):
        txt = self.GetPluginString(filename)
        if txt != '':
            script = self.currentScript
            script.ReplaceSelection('%s\n' % txt)
            script.SetFocus()
            self.AutoUpdateVideo()
            if self.FindFocus() == self.videoWindow:
                self.refreshAVI = True
                self.ShowVideoFrame()

    def GetPluginString(self, filename=''):
        #~ script = self.currentScript
        if not filename or not os.path.isfile(filename):
            filefilter = _('AviSynth plugin (*.dll)|*.dll|All files (*.*)|*.*')
            plugindir = self.options['recentdirPlugins']
            if not os.path.isdir(plugindir):
                plugindir = os.path.join(self.options['avisynthdir'], 'plugins')
            dlg = wx.FileDialog(self, _('Insert a plugin'), plugindir, '', filefilter, wx.OPEN)
            ID = dlg.ShowModal()
            if ID == wx.ID_OK:
                filename = dlg.GetPath()
            else:
                filename = None
            dlg.Destroy()
        if filename:
            txt = 'LoadPlugin("%s")' % filename
            dirname = os.path.dirname(filename)
            if os.path.isdir(dirname):
                self.options['recentdirPlugins'] = dirname
        else:
            txt = ''
        return txt

    def InsertFrameNumber(self):
        script = self.currentScript
        txt = str(self.GetFrameNumber())
        script.ReplaceSelection(txt)
        if self.FindFocus() == self.videoWindow:
            self.refreshAVI = True
            self.ShowVideoFrame()

    def InsertSelectionTrims(self, cutSelected=True, insertMode=0, useDissolve=0):
        script = self.currentScript
        selections = self.GetSliderSelections(invert=cutSelected)
        if not selections:
            return False
        trimText = ' ++ '.join(['Trim(%i, %i)' % (start, stop) for start, stop in selections])
        if useDissolve and len(selections) > 1:
            trimText = 'Dissolve(%s, %s)' % (trimText.replace(' ++', ','), useDissolve-1)
        #~ script.ReplaceSelection(trimText)
        if insertMode == 0:
            self.InsertTextAtScriptEnd(trimText, script)
        elif insertMode == 1:
            script.ReplaceSelection(trimText)
        else:
            text_data = wx.TextDataObject(trimText)
            if wx.TheClipboard.Open():
                wx.TheClipboard.SetData(text_data)
                wx.TheClipboard.Close()
        if insertMode in (0,1):
            self.refreshAVI = True
            # Kill all bookmarks (rebuild non-selection bookmarks...)
            bookmarks = [value for value, bmtype in self.GetBookmarkFrameList() if bmtype ==0]
            newbookmarks = bookmarks[:]
            self.DeleteAllFrameBookmarks(refreshVideo=False)
            gapframes = 0
            framenum = self.GetFrameNumber()
            newframenum = framenum
            nSelections = len(selections)
            for i in xrange(nSelections):
                # Get the current and previous selection endpoints
                if i == 0:
                    a, b = selections[0]
                    c, d = selections[0]
                    gapframes += a
                else:
                    a, b = selections[i-1]
                    c, d = selections[i]
                    gapframes += (c - b - 1)
                # Create the bookmark marking the removed section
                if i != nSelections - 1:
                    self.AddFrameBookmark(d-gapframes, toggle=False, refreshVideo=False)
                # Update the video slider handle position
                if framenum <= d and framenum > b:
                    if framenum >= c:
                        newframenum -= gapframes
                    else:
                        newframenum = (c-gapframes)
                elif i == 0 and framenum <= b:
                    if framenum >= a:
                        newframenum -= gapframes
                    else:
                        newframenum = 0
                # Update the old bookmarks
                for j in xrange(len(bookmarks)):
                    if bookmarks[j] <= d and bookmarks[j] > b:
                        if bookmarks[j] >= c:
                            newbookmarks[j] -= gapframes
                        else:
                            newbookmarks[j] = (c-gapframes)
            for newbookmark in newbookmarks:
                self.AddFrameBookmark(newbookmark, toggle=False, refreshVideo=False)
            self.ShowVideoFrame(newframenum)
        return True

    def GetSliderSelections(self, invert=False):
        script = self.currentScript
        selections = self.videoSlider.GetSelections()
        if not selections:
            return selections
        if not invert:
            return selections
        else:
            invertedselections = []
            nSelections = len(selections)
            lastframe = script.AVI.Framecount - 1
            for i in xrange(nSelections):
                if i == 0:
                    a, b = selections[0]
                    c, d = selections[0]
                    if a != 0:
                        invertedselections.append((0, a-1))
                else:
                    a, b = selections[i-1]
                    c, d = selections[i]
                    invertedselections.append((b+1, c-1))
                if i == nSelections - 1:
                    if d != lastframe:
                        invertedselections.append((d+1, lastframe))
            return invertedselections

    def ValueInSliderSelection(self, value):
        selections = self.GetSliderSelections(self.invertSelection)
        if selections:
            for start, stop in selections:
                if value >= start and value <= stop:
                    return True
        else:
            return None
        return False

    def _x_InsertBookmarkTrims(self):
        script = self.currentScript
        # Get the bookmarks
        bookmarks = self.GetBookmarkFrameList()
        nBookmarks = len(bookmarks)
        if nBookmarks <= 0:
            wx.MessageBox(_('No bookmarks defined!'), _('Error'), style=wx.OK|wx.ICON_ERROR)
            return
        # Sort and make the bookmarks unique (not required?)
        bookmarks.sort()
        #~ bookmarks2 = []
        #~ for bm in bookmarks:
            #~ if bm not in bookmarks2:
                #~ bookmarks2.append(bm)
        #~ bookmarks = bookmarks2
        if nBookmarks == 1:
            wx.MessageBox(_('There must be more than one unique bookmark to use this feature!'), _('Error'), style=wx.OK|wx.ICON_ERROR)
            return
        # Create the Trim commands with pairs of bookmarks
        nPairs = nBookmarks/2
        lastframe = script.AVI.Framecount - 1
        txt = 'Trim(0, '
        for i in xrange(nPairs):
            iA = i * 2
            iB = iA + 1
            lastA = max(bookmarks[iA] - 1, 0)
            firstB = bookmarks[iB]
            txt += '%i) ++ Trim(%i, ' % (lastA, firstB)
        txt += '%i)' % lastframe
        txt = txt.replace('Trim(0, 0) ++ ', '').replace(' ++ Trim(%i, %i)' % (lastframe, lastframe), '')
        script.ReplaceSelection(txt)
        if self.FindFocus() == self.videoWindow:
            self.refreshAVI = True
            # Determine appropriate frame to show
            framenum = self.GetFrameNumber()
            newframenum = framenum
            for i in xrange(nPairs):
                a = bookmarks[i * 2]
                b = bookmarks[i * 2+1]
                if framenum < a:
                    break
                elif framenum < b:
                    newframenum -= (framenum - a)
                    break
                else:
                    newframenum -= (b-a)
            self.ShowVideoFrame(newframenum)

    def InsertTextAtScriptEnd(self, txt, script=None, replaceReturn=False):
        if script is None:
            script = self.currentScript
        text = script.GetText()
        # Find the first valid "return" statement (not in a function)
        lastline = script.GetLineCount() - 1
        maxpos = script.GetTextLength()
        findpos = script.FindText(0, maxpos, 'return', stc.STC_FIND_WHOLEWORD)
        def FindUncommentedText(text, startpos, endpos):
            pos = script.FindText(startpos, endpos, text, 0)
            while pos != -1:
                #~ if script.GetStyleAt(pos) == script.commentStyle:
                if script.GetStyleAt(pos) in script.nonBraceStyles:
                    if startpos < endpos:
                        pos = script.FindText(pos+1, endpos, text, 0)
                    else:
                        pos = script.FindText(pos-1, endpos, text, 0)
                else:
                    return pos
            if startpos < endpos:
                return maxpos + 1
            else:
                return pos
        while findpos != -1:
            # Check if line is commented
            #~ boolComment = script.GetStyleAt(findpos) == script.commentStyle
            boolComment = script.GetStyleAt(findpos) in script.nonBraceStyles
            # Check if the return is inside a function
            openposPre = FindUncommentedText('{', findpos, 0)
            closeposPre = FindUncommentedText('}', findpos, 0)
            openposPost = FindUncommentedText('{', findpos, maxpos)
            closeposPost = FindUncommentedText('}', findpos, maxpos)
            boolFunction = closeposPost < openposPost and openposPre > closeposPre
            # Find the next return if current one is invalid
            if boolComment or boolFunction:
                findpos = script.FindText(findpos+1, maxpos, 'return', stc.STC_FIND_WHOLEWORD)
            else:
                break
        if findpos == -1:
            for line in range(lastline, -1, -1):
                linetxt = script.GetLine(line)
                if linetxt.strip():
                    if linetxt.strip().startswith('#'):
                        continue
                    else:
                        if line < lastline:
                            pos = script.PositionFromLine(line+1)
                            script.GotoPos(pos)
                            script.ReplaceSelection('%s\n' % txt)
                        else:
                            pos = script.GetLineEndPosition(line)
                            script.GotoPos(pos)
                            script.ReplaceSelection('\n%s' % txt)
                    return
            script.GotoPos(0)
            script.ReplaceSelection(txt)
        else:
            line = script.LineFromPosition(findpos)
            endpos = script.GetLineEndPosition(line)
            text = script.GetTextRange(findpos, endpos)
            if text.count('+') > 0 or replaceReturn:
                # Possible conflict with + or ++ shorthand for Aligned/UnalignedSplice()
                script.SetTargetStart(findpos)
                script.SetTargetEnd(findpos+len('return'))
                script.ReplaceTarget('last =')
                while script.GetLine(line).strip()[-1] == '\\' and line < lastline:
                    line += 1
                if line < lastline:
                    pos = script.PositionFromLine(line+1)
                    script.GotoPos(pos)
                    script.ReplaceSelection('return %s\n' % txt)
                else:
                    pos = script.GetLineEndPosition(line)
                    script.GotoPos(pos)
                    script.ReplaceSelection('\nreturn %s' % txt)
            else:
                while script.GetLine(line).strip()[-1] == '\\' and line < lastline:
                    line += 1
                pos = script.GetLineEndPosition(line)
                while unichr(script.GetCharAt(pos-1)).strip() == '' or script.GetStyleAt(pos-1) in script.nonBraceStyles:
                    pos -= 1
                script.GotoPos(pos)
                script.ReplaceSelection('.%s' % txt)

    def GetBookmarkFrameList(self):
        bookmarks = self.videoSlider.GetBookmarks()
        return bookmarks

    def SetBookmarkFrameList(self, bookmarks):
        self.DeleteAllFrameBookmarks()
        lastindex = len(bookmarks) - 1
        for i, item in enumerate(bookmarks):
            try:
                value, bmtype = item
            except TypeError:
                value = item
                bmtype = 0
            if i != lastindex:
                self.AddFrameBookmark(value, bmtype, refreshProgram=False)
            else:
                self.AddFrameBookmark(value, bmtype, refreshProgram=True)

    def DeleteFrameBookmark(self, value, bmtype=0, refreshVideo=True, refreshProgram=True):
        sliderList = [self.videoSlider]
        if self.separatevideowindow:
            sliderList.append(self.videoSlider2)
        for slider in sliderList:
            if value is None:
                slider.RemoveAllBookmarks()
            else:
                slider.RemoveBookmark(value, bmtype, refresh=refreshProgram)
        if refreshProgram:
            self.UpdateBookmarkMenu()
            if refreshVideo and self.trimDialog.IsShown():
                self.ShowVideoFrame()

    def DeleteAllFrameBookmarks(self, bmtype=None, refreshVideo=True):
        if bmtype is None:
            self.DeleteFrameBookmark(None, refreshVideo=refreshVideo)
        else:
            sliderList = [self.videoSlider]
            if self.separatevideowindow:
                sliderList.append(self.videoSlider2)
            for slider in sliderList:
                #~ bmList = self.GetBookmarkFrameList()
                bmList = slider.GetBookmarks()
                lastindex = len(bmList) - 1
                for i, (value, bmType) in enumerate(bmList):
                    if bmtype == bmType:
                        if i < lastindex:
                            slider.RemoveBookmark(value, bmtype, refresh=False)
                        else:
                            slider.RemoveBookmark(value, bmtype, refresh=True)
            self.UpdateBookmarkMenu()

    def AddFrameBookmark(self, value, bmtype=0, toggle=True, refreshVideo=True, refreshProgram=True):
        #~ sliderList = [self.videoSlider]
        #~ if self.separatevideowindow:
            #~ sliderList.append(self.videoSlider2)
        sliderList = self.GetVideoSliderList()
        if not toggle:
            for slider in sliderList:
                slider.SetBookmark(value, bmtype)
        else:
            # Check if bookmark already exists
            bookmarks = self.GetBookmarkFrameList()
            try:
                index = [x for x, y in bookmarks].index(value)
                value, bmtype2 = bookmarks[index]
                for slider in sliderList:
                    if bmtype != bmtype2:
                        slider.SetBookmark(value, bmtype, refresh=refreshProgram)
                    else:
                        self.DeleteFrameBookmark(value, bmtype, refreshProgram=refreshProgram)
                        #~ self.DeleteFrameBookmark(value, bmtype)
            except ValueError:
                # Bookmark does not already exists
                for slider in sliderList:
                    slider.SetBookmark(value, bmtype, refresh=refreshProgram)
        if refreshProgram:
            self.UpdateBookmarkMenu()
            if refreshVideo and self.trimDialog.IsShown():
                self.ShowVideoFrame()

    def GetVideoSliderList(self):
        sliderList = [self.videoSlider]
        if self.separatevideowindow:
            sliderList.append(self.videoSlider2)
        return sliderList

    def UpdateBookmarkMenu(self, event=None):
        #~ bookmarks = [bookmark for bookmark, bmtype in self.GetBookmarkFrameList()]
        #~ nBookmarks = len(bookmarks)
        for i in xrange(self.menuBookmark.GetMenuItemCount()-4):
            self.menuBookmark.DestroyItem(self.menuBookmark.FindItemByPosition(0))
        pos = 0
        bookmarkList = self.GetBookmarkFrameList()
        #~for key in self.bookmarkDict.keys():
            #~if (key, 0) not in bookmarkList:
                #~del self.bookmarkDict[key]
        sortItem = self.menuBookmark.FindItemByPosition(1)
        timecodeItem = self.menuBookmark.FindItemByPosition(2)
        titleItem = self.menuBookmark.FindItemByPosition(3)
        if sortItem.IsChecked():
            bookmarkList.sort()
        width = len(str(max(bookmarkList)[0])) if bookmarkList else 0
        fmt = '%%%dd ' % width
        for bookmark, bmtype in bookmarkList:
            if bmtype == 0:
                label = fmt % bookmark
                if timecodeItem.IsChecked():
                    if self.currentScript.AVI:
                        sec = bookmark / self.currentScript.AVI.Framerate
                        min, sec = divmod(sec, 60)
                        hr, min = divmod(min, 60)
                        label += '[%02d:%02d:%06.3f]' % (hr, min, sec)
                    else:
                        label += '[??:??:??.???]'
                if titleItem.IsChecked():
                    label += ' ' + self.bookmarkDict.get(bookmark, '')
                menuItem = self.menuBookmark.Insert(pos, wx.ID_ANY, label, _('Jump to specified bookmark'))
                self.Bind(wx.EVT_MENU, self.OnMenuVideoGotoFrameNumber, menuItem)
                pos += 1

    def SetSelectionEndPoint(self, bmtype):
        if bmtype not in (1,2):
            return
        if not self.trimDialog.IsShown():
            self.OnMenuVideoTrimEditor(None)
        self.AddFrameBookmark(self.GetFrameNumber(), bmtype)

    def GetFrameNumber(self):
        return self.videoSlider.GetValue()

    def InsertUserSlider(self):
        script = self.currentScript
        sliderTexts, sliderProperties = self.GetScriptSliderProperties(script.GetText())
        #~ labels = [str(p[0].strip('"')) for p in sliderProperties]
        labels = []
        for p in sliderProperties:
            if p is None:
                continue
            try:
                temp = str(p[0].strip('"'))
            except UnicodeEncodeError:
                temp = p[0].strip('"')
            labels.append(temp)
        # Check if user selected a number to replace
        txt = script.GetSelectedText()
        try:
            float(txt)
            dlg = UserSliderDialog(self, labels, initialValueText=txt)
        except ValueError:
            dlg = UserSliderDialog(self, labels)
        ID = dlg.ShowModal()
        if ID == wx.ID_OK:
            script.ReplaceSelection(dlg.GetSliderText())
            if self.FindFocus() == self.videoWindow:
                self.refreshAVI = True
                self.ShowVideoFrame()
        dlg.Destroy()

    def SetScriptStatusText(self, line=None, col=None):
        if line==None or col==None:
            script = self.currentScript
            pos = script.GetCurrentPos()
            line = script.LineFromPosition(pos)
            col = script.GetColumn(pos)
        line += 1
        text = _('Line: %(line)i  Col: %(col)i') % locals()
        statusBar = self.GetStatusBar()
        width = min(statusBar.GetClientSize()[0] - statusBar.GetTextExtent(text)[0] - 6,
                    statusBar.GetTextExtent(text)[0] + 40)
        width = max(0, width)
        statusBar.SetStatusWidths([-1, width])
        statusBar.SetStatusText(text, 1)
        #~ self.SetStatusWidths([-1, 0])
        #~ self.SetStatusText(' '+_('Line: %(line)i  Col: %(col)i') % locals())

    def SetVideoStatusText(self, frame=None, primary=True, addon=''):
        if self.cropDialog.IsShown():
            self.SetVideoCropStatusText()
            return
        if not frame:
            frame = self.videoSlider.GetValue()
        script = self.currentScript
        if script.AVI:
            text = (' '+self.videoStatusBarInfoParsed+'      ') % self.GetVideoInfoDict(script, frame, addon)
        else:
            text = ' %s %i'  % (_('Frame'), frame)
        text2 = text.rsplit('\\T\\T', 1)
        if primary:
            if len(text2) == 2:
                statusBar = self.GetStatusBar()
                width = min(statusBar.GetClientSize()[0] - statusBar.GetTextExtent(text2[0])[0] - 6,
                            statusBar.GetTextExtent(text2[1])[0] + 18)
                if width < 0:
                    width = 0
                statusBar.SetStatusWidths([-1, width])
                statusBar.SetStatusText(text2[0], 0)
                statusBar.SetStatusText(text2[1], 1)
            else:
                self.SetStatusWidths([-1, 0])
                self.SetStatusText(text)
        if self.separatevideowindow:
            if len(text2) == 2:
                width = min(self.videoStatusBar.GetClientSize()[0] - self.videoStatusBar.GetTextExtent(text2[0])[0] - 6,
                            self.videoStatusBar.GetTextExtent(text2[1])[0] + 18)
                if width < 0:
                    width = 0
                self.videoStatusBar.SetStatusWidths([-1, width])
                self.videoStatusBar.SetStatusText(text2[0], 0)
                self.videoStatusBar.SetStatusText(text2[1], 1)
            else:
                self.videoStatusBar.SetStatusWidths([-1, 0])
                self.videoStatusBar.SetStatusText(text)

    def SetVideoCropStatusText(self):
        script = self.currentScript
        left = self.cropValues['left']
        top = self.cropValues['top']
        mright = self.cropValues['-right']
        mbottom = self.cropValues['-bottom']
        wcrop = script.AVI.Width - left - mright
        if wcrop % 32 == 0:
            wmod = 'WMOD = 32'
        elif wcrop % 16 == 0:
            wmod = 'WMOD = 16'
        elif wcrop % 8 == 0:
            wmod = 'WMOD =  8'
        elif wcrop % 4 == 0:
            wmod = 'WMOD =  4'
        elif wcrop % 2 == 0:
            wmod = 'WMOD =  2'
        else:
            wmod = 'WMOD =  1'
        hcrop = script.AVI.Height - top - mbottom
        if hcrop % 32 == 0:
            hmod = 'HMOD = 32'
        elif hcrop % 16 == 0:
            hmod = 'HMOD = 16'
        elif hcrop % 8 == 0:
            hmod = 'HMOD =  8'
        elif hcrop % 4 == 0:
            hmod = 'HMOD =  4'
        elif hcrop % 2 == 0:
            hmod = 'HMOD =  2'
        else:
            hmod = 'HMOD =  1'
        arCrop = '%.03f:1' % (wcrop / float(hcrop))
        if arCrop == '1.000:1':
            arCrop = '1:1'
        if arCrop == '1.333:1':
            arCrop = '4:3'
        if arCrop == '1.778:1':
            arCrop = '16:9'
        ar = '%.03f:1' % (script.AVI.Width / float(script.AVI.Height))
        if ar == '1.000:1':
            ar = '1:1'
        if ar == '1.333:1':
            ar = '4:3'
        if ar == '1.778:1':
            ar = '16:9'
        text = (
            ' Crop(%i,%i,-%i,-%i) - %ix%i (%s) - %s  %s \\T\\T %ix%i (%s)  -  %.03f fps      ' %
            (
                left, top, mright, mbottom,
                wcrop, hcrop, arCrop, wmod, hmod,
                script.AVI.Width, script.AVI.Height, ar, script.AVI.Framerate
            )
        )
        text2 = text.rsplit('\\T\\T', 1)
        statusBar = self.GetStatusBar()
        width = min(statusBar.GetClientSize()[0] - statusBar.GetTextExtent(text2[0])[0] - 6,
                    statusBar.GetTextExtent(text2[1])[0] + 12)
        if width < 0:
            width = 0
        statusBar.SetStatusWidths([-1, width])
        statusBar.SetStatusText(text2[0], 0)
        statusBar.SetStatusText(text2[1], 1)
        if self.separatevideowindow:
            width = min(self.videoStatusBar.GetClientSize()[0] - self.videoStatusBar.GetTextExtent(text2[0])[0] - 6,
                        self.videoStatusBar.GetTextExtent(text2[1])[0] + 12)
            if width < 0:
                width = 0
            self.videoStatusBar.SetStatusWidths([-1, width])
            self.videoStatusBar.SetStatusText(text2[0], 0)
            self.videoStatusBar.SetStatusText(text2[1], 1)

    def ResetStatusText(self):
        if self.FindFocus() == self.videoWindow:
            #~ self.SetStatusText('video message')
            self.SetVideoStatusText()
        else:
            #~ self.SetStatusText('text message')
            self.SetScriptStatusText()

    def GetVideoInfoDict(self, script=None, frame=None, addon=''):
        if script is None:
            script = self.currentScript
        if script.AVI is None:
            self.UpdateScriptAVI(script)
        if not frame:
            frame = self.videoSlider.GetValue()
        v = script.AVI
        framerate = v.Framerate
        framecount = v.Framecount
        m, s = divmod(frame/framerate, 60)
        h, m = divmod(m, 60)
        time = '%02i:%02i:%06.3f' % (h ,m, s)
        m, s = divmod(framecount/framerate, 60)
        h, m = divmod(m, 60)
        totaltime = '%02i:%02i:%06.3f' % (h ,m, s)
        zoom = ''
        if self.zoomwindow and script.zoomwindow_actualsize is not None:
            width, height = script.zoomwindow_actualsize
            zoomfactor = v.Width / float(width)
            zoom  = '(%.2fx) ' % zoomfactor
            zoom  = '(%.2fx) ' % zoomfactor
        else:
            width, height = v.Width, v.Height
            if self.zoomfactor != 1:
                if self.zoomfactor < 1 or self.zoomwindow:
                    zoom = '(%.2fx) ' % self.zoomfactor
                else:
                    zoom = '(%ix) ' % self.zoomfactor
        aspectratio = '%.03f:1' % (width / float(height))
        if aspectratio == '1.000:1':
            aspectratio = '1:1'
        if aspectratio == '1.333:1':
            aspectratio = '4:3'
        if aspectratio == '1.778:1':
            aspectratio = '16:9'
        if addon:
            pixelpos, pixelhex, pixelrgb, pixelrgba, pixelyuv = addon
            if v.IsYUY2 or v.IsYV12:
                pixelclr = pixelyuv
            elif v.IsRGB32:
                pixelclr = pixelrgba
            else:
                pixelclr = pixelrgb
        else:
            pixelpos, pixelhex, pixelrgb, pixelrgba, pixelyuv, pixelclr = '', '', '', '', '', ''
        frameratenum, framerateden, audiorate, audiolength, audiochannels, audiobits, colorspace, parity = v.FramerateNumerator, v.FramerateDenominator, v.Audiorate, v.Audiolength, v.Audiochannels, v.Audiobits, v.Colorspace, v.GetParity
        if v.IsFrameBased:
            fieldframebased = _('Frame Based')
        else:
            fieldframebased = _('Field Based')
        if parity == 0:
            parity = _('Bottom Field First')
            parityshort = _('BFF')
        else:
            parity = _('Top Field First')
            parityshort = _('TFF')
        if v.IsAudioInt:
            audiotype = _('Integer')
        else:
            audiotype = _('Float')
        return locals()

    def ParseVideoStatusBarInfo(self, info):
        showVideoPixelInfo = False
        showVideoPixelAvisynth = False
        for item in ('%POS', '%HEX', '%RGB', '%YUV', '%CLR'):
            if info.count(item) > 0:
                showVideoPixelInfo = True
                if item in ('%YUV', '%CLR'):
                    showVideoPixelAvisynth = True
        keyList = [
            ('%POS', '%(pixelpos)s'),
            ('%HEX', '%(pixelhex)s'),
            ('%RGB', '%(pixelrgb)s'),
            ('%YUV', '%(pixelyuv)s'),
            ('%CLR', '%(pixelclr)s'),
            ('%FRN', '%(frameratenum)i'),
            ('%FRD', '%(framerateden)i'),
            ('%AUR', '%(audiorate).03f'),
            ('%AUL', '%(audiolength)i'),
            ('%AUC', '%(audiochannels)i'),
            ('%AUB', '%(audiobits)i'),
            ('%AUT', '%(audiotype)i'),
            ('%FC', '%(framecount)i'),
            ('%TT', '%(totaltime)s'),
            ('%FR', '%(framerate).03f'),
            ('%CS', '%(colorspace)s'),
            ('%AR', '%(aspectratio)s'),
            ('%FB', '%(fieldframebased)s'),
            ('%PS', '%(parityshort)s'),
            ('%W', '%(width)i'),
            ('%H', '%(height)i'),
            ('%F', '%(frame)s'),
            ('%T', '%(time)s'),
            ('%P', '%(parity)s'),
            ('%Z', '%(zoom)s'),
        ]
        for key, item in keyList:
            info = info.replace(key, item)
        return info, showVideoPixelInfo, showVideoPixelAvisynth

    def SelectTab(self, index=None, inc=0):
        nTabs = self.scriptNotebook.GetPageCount()
        if nTabs == 1:
            self.scriptNotebook.SetSelection(0)
            return True
        if index is None:
            index = inc + self.scriptNotebook.GetSelection()
            # Allow for wraparound with user-specified inc
            if index<0:
                index = nTabs - abs(index) % nTabs
                if index == nTabs:
                    index = 0
            if index > nTabs-1:
                index = index % nTabs
        # Limit index if specified directly by user
        if index < 0:
            return False
        if index > nTabs - 1:
            return False
        if not self.separatevideowindow:
            self.scriptNotebook.SetSelection(index)
        else:
            self.Freeze()
            self.scriptNotebook.SetSelection(index)
            self.Thaw()
        if self.previewWindowVisible:
            if self.FindFocus() == self.currentScript:
                self.IdleCall.append((self.SetScriptStatusText, tuple(), {}))
            self.IdleCall.append((self.OnMouseMotionVideoWindow, tuple(), {}))
        return True

    def ShowFunctionDefinitionDialog(self, functionName=None):
        dlg = AvsFunctionDialog(
            self,
            self.optionsFilters,
            self.options['filteroverrides'],
            self.options['filterpresets'],
            self.options['filterremoved'],
            self.options['autcompletetypeflags'],
            self.installedfilternames,
            functionName=functionName,
            CreateDefaultPreset=self.currentScript.CreateDefaultPreset,
            ExportFilterData=self.ExportFilterData,
            
        )
        ID = dlg.ShowModal()
        if ID == wx.ID_OK:
            self.options['filteroverrides'] = dlg.GetOverrideDict()
            self.options['filterremoved'] = dlg.GetRemovedSet()
            self.options['filterpresets'] = dlg.GetPresetDict()
            self.options['autcompletetypeflags'] = dlg.GetAutcompletetypeFlags()
            self.defineScriptFilterInfo()
            for i in xrange(self.scriptNotebook.GetPageCount()):
                script = self.scriptNotebook.GetPage(i)
                script.Colourise(0, script.GetTextLength())
        dlg.Destroy()

    def _x_ShowFunctionDefinitionDialog(self, functionName=None):
        # Build and show the dialog
        startDirectory = self.options['lasthelpdir']
        if startDirectory is None:
            startDirectory = self.options['avisynthdir']
            if startDirectory is None:
                startDirectory = '.'
        dlg = AvsFunctionDialog(
            self,
            (self.optionsFilters, self.optionsFilterPresets, self.optionsFilterDocpaths, self.optionsFilterTypes, self.optionsKeywordLists),
            title=_('Edit AviSynth function information'),
            keyTitle=_('  Function name'),
            valueTitle=_('Function arguments'),
            editable=True,
            insertable=True,
            functionName=functionName,
            startDirectory=startDirectory,
        )
        ID = dlg.ShowModal()
        # Set the data
        if ID == wx.ID_OK:
            self.optionsFilters, self.optionsFilterPresets, self.optionsFilterDocpaths, self.optionsFilterTypes, self.optionsKeywordLists = dlg.GetDict()
            self.options['lasthelpdir'] = dlg.GetLastDirectory()
            for index in xrange(self.scriptNotebook.GetPageCount()):
                script = self.scriptNotebook.GetPage(index)
                script.DefineKeywordCalltipInfo(self.optionsFilters, self.optionsFilterPresets, self.optionsFilterDocpaths, self.optionsFilterTypes, self.optionsKeywordLists)
        dlg.Destroy()

    def _x_ShowFunctionExportImportDialog(self, export=True):
        if export:
            infoDict = (self.optionsFilters, self.optionsFilterPresets, self.optionsFilterDocpaths, self.optionsFilterTypes)
        else:
            # Prompt for the import file
            dlg2 = wx.FileDialog(
                self,
                _('Open filter customization file'),
                self.programdir,
                '',
                '%s|%s' % (_('Filter customization file (*.tag)|*.tag'), _('Calltip-only text file (*.txt)|*.txt')),
                wx.OPEN
            )
            ID = dlg2.ShowModal()
            if ID == wx.ID_OK:
                filename = dlg2.GetPath()
                dlg2.Destroy()
                ext = os.path.splitext(filename)[1]
                if ext == '.tag':
                    f = open(filename, mode='rb')
                    try:
                        tempDict = cPickle.load(f)
                        f.close()
                    except cPickle.UnpicklingError:
                        wx.MessageBox(_('Invalid filter customization file!'), _('Error'), style=wx.OK|wx.ICON_ERROR)
                        f.close()
                        dlg2.Destroy()
                        return
                    optionsFilters = dict([(k,v[0]) for k,v in tempDict.items()])
                    optionsFilterPresets = dict([(k,v[1]) for k,v in tempDict.items()])
                    optionsFilterDocpaths = dict([(k,v[2]) for k,v in tempDict.items()])
                    optionsFilterTypes = dict([(k,v[3]) for k,v in tempDict.items()])
                elif ext == '.txt':
                    f = open(filename, mode='r')
                    text = f.read()
                    f.close()
                    filterInfoList = text.split('\n\n')
                    optionsFilters = {}
                    for s in filterInfoList:
                        splitstring = s.split('(', 1)
                        if len(splitstring) == 2:
                            optionsFilters[splitstring[0].strip()] = '('+splitstring[1].strip(' ')
                    optionsFilterPresets = dict([(k,None) for k in optionsFilters.keys()])
                    optionsFilterDocpaths = dict([(k,None) for k in optionsFilters.keys()])
                    optionsFilterTypes = dict([(k,None) for k in optionsFilters.keys()])
                infoDict = (optionsFilters, optionsFilterPresets, optionsFilterDocpaths, optionsFilterTypes)
            else:
                dlg2.Destroy()
                return
        # Build and show the export/import dialog
        dlg = AvsFunctionExportImportDialog(self, infoDict, export=export)
        ID = dlg.ShowModal()
        # Set the data
        if ID == wx.ID_OK:
            dataDict = dlg.GetData()
            if export:
                # Prompt to save the export file
                dlg2 = wx.FileDialog(
                    self,
                    _('Save filter customization file'),
                    self.programdir,
                    '',
                    '%s|%s' % (_('Filter customization file (*.tag)|*.tag'), _('Calltip-only text file (*.txt)|*.txt')),
                    wx.SAVE | wx.OVERWRITE_PROMPT
                )
                ID = dlg2.ShowModal()
                if ID == wx.ID_OK:
                    filename = dlg2.GetPath()
                    dlg2.Destroy()
                    ext = os.path.splitext(filename)[1]
                    if ext == '.tag':
                        f = open(filename, mode='wb')
                        cPickle.dump(dataDict, f, protocol=0)
                        f.close()
                    elif ext == '.txt':
                        keys = dataDict.keys()
                        keys.sort()
                        textlines = []
                        for key in keys:
                            textlines.append(key+dataDict[key][0].split('\n\n')[0])
                            textlines.append('')
                        f = open(filename, 'w')
                        f.write('\n'.join(textlines))
                        f.close()
                else:
                    dlg2.Destroy()
                    dlg.Destroy()
                    return
            else:
                # Overwrite AvsP filter information using the imported data
                overwriteAll = dlg.GetOverwriteAll()
                self.UpdateFunctionDefinitions(dataDict, overwriteAll=overwriteAll, wrapCalltip=False)
        dlg.Destroy()

    def _x_UpdateFunctionDefinitions(self, filterInfo, overwriteAll=False, wrapCalltip=True):
        # Validate the filterInfo input
        if type(filterInfo) != dict:
            wx.MessageBox(_('Invalid argument!'), _('Error'), style=wx.OK|wx.ICON_ERROR)
            return
        for value in filterInfo.values():
            if len(value) != 4:
                wx.MessageBox(_('Invalid argument!'), _('Error'), style=wx.OK|wx.ICON_ERROR)
                return
        # Create filter info data structure to iterate upon
        a, b, c, d = self.optionsFilters, self.optionsFilterPresets, self.optionsFilterDocpaths, self.optionsFilterTypes
        filterDataDict = dict([(key, (a[key], b[key], c[key], d[key])) for key in self.optionsFilters.keys()])
        filterDataDictKeys = filterDataDict.keys()
        filterDataDictKeysLower = [s.lower() for s in filterDataDictKeys]
        # Update the filter information
        for key, value in filterInfo.items():
            newCalltip, newPreset, newDocpath, newFilterType = value
            # Wrap the newCalltip as necessary
            if wrapCalltip:
                newCalltip = self.wrapFilterCalltip(newCalltip)
            # Validate the newDocpath, set to empty string if invalid
            if newDocpath is not None:
                if not newDocpath.startswith('http://') and not os.path.isfile(newDocpath):
                    newDocpath = ''
            newValue = [newCalltip, newPreset, newDocpath, newFilterType]
            try:
                # Update the existing info
                index = filterDataDictKeysLower.index(key.lower())
                oldkey = filterDataDictKeys[index]
                oldCalltip, oldPreset, oldDocpath, oldFilterType = filterDataDict[oldkey]
                if overwriteAll:
                    if oldkey != key:
                        del filterDataDict[oldkey]
                    for i, oldItem in enumerate((oldCalltip, oldPreset, oldDocpath, oldFilterType)):
                        if newValue[i] is None:
                            newValue[i] = oldItem
                    filterDataDict[key] = newValue
                else:
                    if oldCalltip or newValue[0] is None: newValue[0] = oldCalltip
                    if oldPreset or newValue[1] is None: newValue[1] = oldPreset
                    if oldDocpath or newValue[2] is None: newValue[2] = oldDocpath
                    if True: newValue[3] = oldFilterType
                    filterDataDict[oldkey] = newValue
            except ValueError:
                # Key does not exist, add the new info
                for i in xrange(len(newValue)):
                    if newValue[i] is None:
                        newValue[i] = ''
                        if i == 3:
                            newValue[i] = 0
                filterDataDict[key] = newValue
        self.optionsFilters = dict([(key, value[0]) for key, value in filterDataDict.items()])
        self.optionsFilterPresets = dict([(key, value[1]) for key, value in filterDataDict.items()])
        self.optionsFilterDocpaths = dict([(key, value[2]) for key, value in filterDataDict.items()])
        self.optionsFilterTypes = dict([(key, value[3]) for key, value in filterDataDict.items()])
        # Update the open scripts to reflect filter info changes
        for index in xrange(self.scriptNotebook.GetPageCount()):
            script = self.scriptNotebook.GetPage(index)
            script.DefineKeywordCalltipInfo(self.optionsFilters, self.optionsFilterPresets, self.optionsFilterDocpaths, self.optionsFilterTypes, self.optionsKeywordLists)

    def HidePreviewWindow(self):
        if not self.separatevideowindow:
            self.mainSplitter.Unsplit()
        else:
            self.videoDialog.Hide()
        #~ self.sizer.Show(self.previewWindow, 0, 0)
        #~ self.sizer.Layout()
        self.previewWindowVisible = False
        #~ self.RefitWindow(move=False)

        try:
            if self.cropDialog.IsShown():
                self.OnCropDialogCancel(None)
        except AttributeError:
            pass

        self.toggleButton.SetBitmapLabel(self.bmpVidUp)
        self.toggleButton.Refresh()

        self.currentScript.SetFocus()

    def ShowVideoFrame(self, framenum=None, forceRefresh=False, wrap=True, script=None, userScrolling=False, forceLayout=False, doLayout=True, resize=None, focus=True):
        # Exit if disable preview option is turned on
        if self.options['disablepreview']:
            return
        # Update the script AVI
        if script is None:
            script = self.currentScript
        if script.AVI is None:
            forceRefresh = True
        if self.UpdateScriptAVI(script, forceRefresh) is None:
            #~ wx.MessageBox(_('Error loading the script'), _('Error'), style=wx.OK|wx.ICON_ERROR)
            return False
        #~ # Exit if invalid user sliders
        #~ labels = []
        #~ for sliderText in script.sliderTexts:
            #~ try:
                #~ label, minValue, maxValue, value = self.parseSliderText(sliderText)
                #~ labels.append(label)
            #~ except ValueError:
                #~ pass
        # Reset the video frame slider range if necessary
        if self.videoSlider.GetMax() != script.AVI.Framecount-1:
            self.videoSlider.SetRange(0, script.AVI.Framecount-1)
            if self.separatevideowindow:
                self.videoSlider2.SetRange(0, script.AVI.Framecount-1)
        # Get the desired AVI frame to display
        if framenum is None and self.options['enableframepertab']:
            framenum = script.lastFramenum
        try:
            # assume framenum is an integer
            if framenum is None:
                framenum = self.videoSlider.GetValue()
            framenum += 0
        except TypeError:
            # assume framenum is a string (time)
            timetxt = framenum.split(':')
            if len(timetxt) == 3:
                try:
                    hours = int(timetxt[0])
                    minutes = int(timetxt[1])
                    seconds = float(timetxt[2])
                    total_seconds = hours * 60 * 60 + minutes * 60 + seconds
                    framenum = int(round((script.AVI.Framerate * total_seconds)))
                except ValueError:
                    framenum = 0
            else:
                framenum = 0
        except AttributeError: # don't know what framenum is
            framenum = 0
        if framenum < 0:
            if wrap:
                while framenum < 0:
                    framenum += script.AVI.Framecount
            else:
                framenum = 0
        if framenum >= script.AVI.Framecount:
            framenum = script.AVI.Framecount-1
        self.currentframenum = framenum

        self.videoPaneSizer.Layout()
        #~ self.videoSplitter.UpdateSize()

        # Update sliders...
        doFocusScript = False
        toggleTagNames = [a for a,b in script.toggleTags]
        oldToggleTagNames = [a for a,b in script.oldToggleTags]
        if forceRefresh:
            script.oldSliderTexts = oldToggleTagNames = script.oldAutoSliderInfo = None
        if not userScrolling and (script.sliderTexts != script.oldSliderTexts or toggleTagNames != oldToggleTagNames or script.autoSliderInfo != script.oldAutoSliderInfo):
            if toggleTagNames != oldToggleTagNames:
                self.createToggleTagCheckboxes(script)
            if script.autoSliderInfo != script.oldAutoSliderInfo:
                self.createAutoUserSliders(script)
            if script.sliderTexts != script.oldSliderTexts:
                if not self.createUserSliders(script):
                    #~ return False
                    doFocusScript = True
            script.videoSidebarSizer.Layout()
            script.sliderWindow.FitInside()
            script.sliderWindow.Refresh()

        # Resize the video window as necessary
        oldSize = self.videoWindow.GetVirtualSize()
        videoWidth = w = int(script.AVI.Width * self.zoomfactor)
        videoHeight = h = int(script.AVI.Height * self.zoomfactor)
        if self.zoomwindowfit:
            self.videoWindow.SetVirtualSize((0, 0))
        if doLayout:
            if forceLayout or not self.previewWindowVisible or videoWidth != self.oldWidth or videoHeight != self.oldHeight:
                self.videoWindow.SetVirtualSize((w+self.xo + 2, h+self.yo + 2))
                if resize is None:
                    if self.currentScript.lastSplitVideoPos is not None:
                        resize = False
                    else:
                        resize = True
                self.LayoutVideoWindows(w, h, resize, forceRefresh=forceRefresh)

                self.toggleButton.SetBitmapLabel(self.bmpVidDown)
                self.toggleButton.Refresh()
        else:
            #~ self.videoWindow.Refresh()
            pass
        newSize = self.videoWindow.GetVirtualSize()
        # Force a refresh when resizing the preview window
        oldVideoSize = (self.oldWidth, self.oldHeight)
        newVideoSize = (videoWidth, videoHeight)        
        self.bmpVideo = None
        if newSize != oldSize or newVideoSize != oldVideoSize or not self.previewWindowVisible:
            self.videoWindow.Refresh()
            self.previewWindowVisible = True
        else:
            self.previewWindowVisible = True
            # Paint the frame
            dc = wx.ClientDC(self.videoWindow)
            self.PaintAVIFrame(dc, script, self.currentframenum)
        # Update various elements
        self.videoSlider.SetValue(framenum)
        if (framenum, 0) in self.GetBookmarkFrameList():
            color = wx.RED
        else:
            color = wx.BLACK
        self.frameTextCtrl.SetForegroundColour(color)
        self.frameTextCtrl.Replace(0, -1, str(framenum))
        if self.separatevideowindow:
            self.videoSlider2.SetValue(framenum)
            self.frameTextCtrl2.SetForegroundColour(color)
            self.frameTextCtrl2.Replace(0, -1, str(framenum))
        # If error clip, highlight the line with the error
        errmsg = script.AVI.error_message
        if errmsg is not None and not self.options['autoupdatevideo']:
            #~ items = errmsg.lower().split()
            lines = errmsg.lower().split('\n')
            items = lines[-1].split()
            try:
                index = items.index('line') + 1
                if index < len(items):
                    try:
                        linenum = int(items[index].strip('),')) - 1
                        if linenum < script.GetLineCount():
                            posA = script.PositionFromLine(linenum)
                            posB = script.GetLineEndPosition(linenum)
                            script.SetSelection(posA, posB)
                            doFocusScript = True
                    except ValueError:
                        pass
            except ValueError:
                pass
        if doFocusScript:
            #~ self.HidePreviewWindow()
            script.SetFocus()
            script.EnsureCaretVisible()
        else:
            if focus:
                self.videoWindow.SetFocus()
                #~ self.SetVideoStatusText(framenum)
                # Update pixel info if cursor in preiew windows
                self.IdleCall.append((self.OnMouseMotionVideoWindow, tuple(), {}))
            else:
                primary = False
                if self.FindFocus() == self.videoWindow:
                    primary = True
                self.SetVideoStatusText(framenum, primary=primary)
        # Store video information (future use)
        self.oldWidth = videoWidth
        self.oldHeight = videoHeight
        self.oldFramecount = script.AVI.Framecount
        script.oldSliderTexts = script.sliderTexts
        script.oldAutoSliderInfo = script.autoSliderInfo
        script.oldToggleTags = script.toggleTags
        script.lastFramenum = framenum
        return True

    def LayoutVideoWindows(self, w=None, h=None, resize=True, forcefit=False, forceRefresh=False):
        if w is None:
            w = int(self.currentScript.AVI.Width * self.zoomfactor)
        if h is None:
            h = int(self.currentScript.AVI.Height * self.zoomfactor)
        # Show or hide slider window
        #~ if not self.zoomwindowfit or self.separatevideowindow:
        if True:
            boolSliders = bool(self.currentScript.sliderTexts or self.currentScript.sliderProperties or self.currentScript.toggleTags or self.currentScript.autoSliderInfo)
            if boolSliders:
                self.toggleSliderWindowButton.Enable()
                if self.currentScript.sliderWindowShown:
                    self.currentScript.sliderWindow.Show()

                    #~ window2 = self.videoSplitter.GetWindow2()
                    #~ if window2 != self.currentScript.sliderWindow:
                        #~ self.videoSplitter.ReplaceWindow(window2, self.currentScript.sliderWindow)
                    #~ else:
                        #~ self.videoSplitter.SetSashPosition(self.currentScript.lastSplitSliderPos)
                    self.ShowSliderWindow(self.currentScript)

                else:
                    if forceRefresh and not self.videoSplitter.IsSplit() and not self.options['keepsliderwindowhidden'] and not self.currentScript.userHidSliders:
                        self.ToggleSliderWindow()
                        #~ pass
                    else:
                        self.HideSliderWindow(self.currentScript)
            else:
                #~ if self.currentScript.sliderWindowShown:
                    #~ self.ToggleSliderWindow()
                #~ else:
                    #~ self.videoSplitter.SetSashPosition(-self.videoSplitter.GetMinimumPaneSize())
                self.currentScript.sliderWindowShown = True
                self.ToggleSliderWindow()
                self.toggleSliderWindowButton.Disable()
        if self.separatevideowindow:
            if self.options['allowresize'] and not self.videoDialog.IsMaximized():
                #~ sizer = self.videoDialog.GetSizer()
                #~ sizer.SetItemMinSize(0, w + 2*self.xo + 300, h + 2*self.yo)
                #~ sizer.Fit(self.videoDialog)
                wA, hA = self.videoDialog.GetSize()
                if self.currentScript.sliderWindowShown:
                    wslider = -self.currentScript.lastSplitSliderPos
                else:
                    wslider = self.videoSplitter.GetMinimumPaneSize() + 5
                wB = (w + 2*self.xo + 20) + (wslider) + self.toggleSliderWindowButton.GetSize()[0] + 5
                hB = (h + 2*self.yo) + 75# + (200)
                #~ wC, hC = wx.ScreenDC().GetSize()
                winpos = self.videoDialog.GetPosition()
                imonitor = max(0, wx.Display.GetFromPoint(winpos))
                display = wx.Display(imonitor)
                wC, hC = display.GetGeometry().GetSize()
                if wB > 0.9 * wC:
                    wB = wA
                if hB > 0.9 * hC:
                    hB = hA
                #~ newsize = (max(wA, wB), max(hA, hB))
                newsize = (max(wA, wB), hB)
                if not self.zoomwindow and newsize != (wA, hA):
                    self.videoDialog.SetSize(newsize)
                    # Move the window if it's offscreen
                    size = self.videoDialog.GetSize()
                    pos = self.videoDialog.GetPosition()
                    if (pos[0]+size[0]>wC) or (pos[1]+size[1]>hC):
                        self.videoDialog.Center()
            self.SetProgramTitle()
            #~ self.videoDialog.SetTitle(_('AvsP preview') + '  -  ' + self.getScriptTabname(allowfull=False))
            self.videoDialog.Show()
            #~ self.videoSplitter.SetSashPosition(self.currentScript.lastSplitSliderPos)
            return
        if resize and self.options['allowresize'] and not self.IsMaximized():
            # Resize the window as necessary
            wA, hA = self.GetSize()
            #~ wB = (w + 2*self.xo + 20) + (self.currentScript.sliderSizer.GetMinSize()[0] + 30) + 5
            if self.currentScript.sliderWindowShown:
                wslider = -self.currentScript.lastSplitSliderPos
            else:
                wslider = self.videoSplitter.GetMinimumPaneSize() + 5
            wB = (w + 2*self.xo + 20) + (wslider) + self.toggleSliderWindowButton.GetSize()[0] + 5
            hB = (h + 2*self.yo) + (200)
            #~ wC, hC = wx.ScreenDC().GetSize()
            winpos = self.GetPosition()
            index = max(0, wx.Display.GetFromPoint(winpos))
            display = wx.Display(index)
            wC, hC = display.GetGeometry().GetSize()
            if wB > 0.9 * wC:
                wB = wA
            if hB > 0.9 * hC:
                hB = hA
            newsize = (max(wA, wB), max(hA, hB))
            if newsize != (wA, hA):
                self.SetSize(newsize)
                # Move the window if it's offscreen
                size = self.GetSize()
                pos = self.GetPosition()
                if (pos[0]+size[0]>wC) or (pos[1]+size[1]>hC):
                    self.Center()
        #~ if self.lastSplitVideoPos is not None:
            #~ self.lastSplitVideoPos = self.mainSplitter.GetSashPosition()
        # Set the splitter positions
        self.SplitVideoWindow(h, forcefit=forcefit)
        #~ self.SplitSliderWindow(w)

    def SplitVideoWindow(self, h=None, forcefit=False):
        y = self.GetMainSplitterNegativePosition(h=h, forcefit=forcefit)
        if self.mainSplitter.IsSplit():
            self.mainSplitter.SetSashPosition(y)
        else:
            self.mainSplitter.SplitHorizontally(self.scriptNotebook, self.videoPane, y)

    def GetMainSplitterNegativePosition(self, h=None, forcefit=False):
        if not forcefit and self.currentScript.lastSplitVideoPos is not None:
            y = self.currentScript.lastSplitVideoPos
        else:
            script = self.currentScript
            if self.zoomwindow and script.zoomwindow_actualsize is not None:
                h = None
            if h is None:
                if self.zoomwindow and script.zoomwindow_actualsize is not None:
                    vidheight = script.zoomwindow_actualsize[1]
                else:
                    if script.AVI is None:
                        #~ self.UpdateScriptAVI(script, forceRefresh=True)
                        vidheight = 0
                    else:
                        vidheight = script.AVI.Height
                h = int(vidheight * self.zoomfactor)
            #~ y = -(h + 2 * self.yo +5) # + 15)
            y = -(h + 2 * self.yo + 5 + self.mainSplitter.GetSashSize()/2)
        return y

    def ToggleSliderWindow(self, vidrefresh=False):
        self.videoPaneSizer.Layout()
        # TODO...
        if True: #button.IsEnabled():
            #~ self.SplitSliderWindow(forcefit=True)
            if self.currentScript.sliderWindowShown:
                self.HideSliderWindow(self.currentScript)
            else:
                self.ShowSliderWindow(self.currentScript)
        if vidrefresh:
            #~ self.IdleCall = (self.ShowVideoFrame, tuple(), {'forceRefresh': True, 'focus': False})
            if self.zoomwindowfit:
                self.ShowVideoFrame(focus=False, doLayout=False)
                #~ self.ShowVideoFrame(forceRefresh=True, focus=False, doLayout=False)
                #~ self.videoWindow.Refresh()
            #~ wx.FutureCall(100, self.ShowVideoFrame, forceRefresh=True, focus=False)

    def ShowSliderWindow(self, script):
        button = self.toggleSliderWindowButton
        # Show the sliders
        #~ self.videoSplitter.SetSashPosition(self.currentScript.lastSplitSliderPos)
        if self.videoSplitter.IsSplit():
            #~ self.videoSplitter.Unsplit()
            #~ self.videoSplitter.SplitVertically(self.videoWindow, script.sliderWindow, self.currentScript.lastSplitSliderPos)
            self.videoSplitter.ReplaceWindow(self.videoSplitter.GetWindow2(), script.sliderWindow)
            self.videoSplitter.SetSashPosition(self.currentScript.lastSplitSliderPos)
        else:
            self.videoSplitter.SplitVertically(self.videoWindow, script.sliderWindow, self.currentScript.lastSplitSliderPos)
        #~ self.currentScript.lastSplitSliderPos = self.videoSplitter.GetSashPosition() - self.videoSplitter.GetClientSize()[0]
        script.sliderWindow.Show()
        script.sliderWindowShown = True
        button.SetBitmapLabel(button.bmpHide)
        #~ button.SetToolTip(wx.ToolTip(_('Hide slider window')))
        button.Refresh()

    def HideSliderWindow(self, script):
        button = self.toggleSliderWindowButton
        # Hide the sliders
        #~ self.videoSplitter.SetSashPosition(-self.videoSplitter.GetMinimumPaneSize())
        self.videoSplitter.Unsplit()
        script.sliderWindow.Hide()
        script.sliderWindowShown = False
        #~ self.currentScript.lastSplitSliderPos = self.videoSplitter.GetSashPosition() - self.videoSplitter.GetClientSize()[0]
        button.SetBitmapLabel(button.bmpShow)
        #~ button.SetToolTip(wx.ToolTip(_('Show slider window')))
        button.Refresh()

    def ShowVideoOffset(self, offset=0, units='frames', focus=True):
        script = self.currentScript
        if script.AVI is None:
            self.UpdateScriptAVI()
        units = units.lower()
        if units == 'frames':
            offsetFrames = offset
        elif units in ('sec', 'seconds'):
            offsetFrames = offset * int(round(script.AVI.Framerate))
        elif units in ('min', 'minutes'):
            offsetFrames = offset * int(round(script.AVI.Framerate * 60))
        elif units in ('hr', 'hours'):
            offsetFrames = offset * int(round(script.AVI.Framerate * 60 * 60))
        framenum = offsetFrames + self.videoSlider.GetValue()
        self.ShowVideoFrame(framenum, wrap=False, script=script, focus=focus)

    def GotoNextBookmark(self, reverse=False):
        current_frame = self.GetFrameNumber()
        bookmarkValues = [value for value, btype in self.GetBookmarkFrameList()]# if btype==0]
        bookmarkValues.sort()
        if len(bookmarkValues) == 0:
            return
        try:
            index = bookmarkValues.index(current_frame)
            if reverse:
                index -= 1
            else:
                index += 1
                if index > len(bookmarkValues) - 1:
                    index = 0
            new_frame = bookmarkValues[index]
        except ValueError:
            # current_frame is not bookmarked, find the nearest appropriate frame
            if not reverse:
                new_frame = None
                for b in bookmarkValues:
                    if b > current_frame:
                        new_frame = b
                        break
                if new_frame is None:
                    new_frame = bookmarkValues[0]
            else:
                new_frame = None
                bookmarkValues.reverse()
                for b in bookmarkValues:
                    if b < current_frame:
                        new_frame = b
                        break
                if new_frame is None:
                    new_frame = bookmarkValues[0]
            #~ diffs = [abs(current_frame-b) for b in bookmarkValues]
            #~ new_frame = bookmarkValues[diffs.index(min(diffs))]
        self.ShowVideoFrame(new_frame)

    def UpdateScriptAVI(self, script=None, forceRefresh=False, prompt=True):
        if not script:
            script = self.currentScript
            scriptIndex = self.scriptNotebook.GetSelection()
        else:
            scriptIndex = 0
            for index in xrange(self.scriptNotebook.GetPageCount()):
                if script == self.scriptNotebook.GetPage(index):
                    scriptIndex = index
        updateDisplayClip = False
        if script.AVI is None:
            self.firstToggled = forceRefresh = True
        elif self.zoomwindow:
            try:
                fitWidth, fitHeight = self.GetFitWindowSize()
                zoomfactorHeight = float(fitHeight) / script.AVI.Height
                if self.zoomwindowfill:
                    self.zoomfactor = zoomfactorHeight
                else:                    
                    zoomfactorWidth = float(fitWidth) / script.AVI.Width
                    self.zoomfactor = min(zoomfactorWidth, zoomfactorHeight)
            except TypeError:
                pass
        fitHeight = fitWidth = None
        #~ if not self.zoomwindow:
            #~ fitHeight = fitWidth = None
        #~ else:
            #~ fitWidth, fitHeight = self.GetFitWindowSize()
            #~ if self.zoomwindowfill:
                #~ fitWidth = None
        #~ if self.zoomwindowfit:
            #~ if script.AVI is not None:
                #~ if script.AVI.Width != fitWidth and script.AVI.Height != fitHeight:
                    #~ forceRefresh = True
                    #~ updateDisplayClip = True
        boolNewAVI = False
        if self.refreshAVI and self.options['refreshpreview'] or forceRefresh:
            # Compare scripts including style, but excluding comment/newline/space
            scripttxt = script.GetStyledText(0, script.GetTextLength())
            styledtxt = []
            for i in range(0, len(scripttxt), 2):
                style = ord(scripttxt[i+1]) & 31
                if style in script.commentStyle\
                or (style == script.STC_AVS_DEFAULT and scripttxt[i] in ' \t\n'):
                    continue
                styledtxt.append(scripttxt[i])
                styledtxt.append(style)
            if styledtxt != script.previewtxt or forceRefresh:
                script.previewtxt = styledtxt
                scripttxt = script.GetText()
                # Replace any user-inserted sliders (defined with self.regexp)
                #~ script.SetFocus()
                #~ newScripttxt = self.getCleanText(scripttxt)
                # Backup the current session if paranoia mode is on
                if self.options['paranoiamode']:
                    self.SaveSession(self.lastSessionFilename, saverecentdir=False, previewvisible=False)
                #~ previewname = self.MakePreviewScriptFile(script)
                #~ AVI = PyAVIFile(previewname)
                sDirname = os.path.dirname(script.filename)
                sBasename = self.scriptNotebook.GetPageText(scriptIndex).lstrip('* ')
                filename = os.path.join(sDirname, sBasename)
                if script.AVI is None:
                    oldFramecount = 240
                    boolOldAVI = False
                else:
                    oldFramecount = script.AVI.Framecount
                    oldWidth, oldHeight = script.AVI.Width, script.AVI.Height
                    boolOldAVI = True
                cwd = os.getcwd()
                if updateDisplayClip and False:
                    script.AVI.CreateDisplayClip(fitHeight, fitWidth)
                else:
                    wx.BeginBusyCursor()
                    script.AVI = None
                    script.AVI = pyavs.AvsClip(self.getCleanText(scripttxt), filename, fitHeight=fitHeight, fitWidth=fitWidth, oldFramecount=oldFramecount, keepRaw=self.showVideoPixelAvisynth, matrix=self.matrix, interlaced=self.interlaced, swapuv=self.swapuv)
                    wx.EndBusyCursor()
                os.chdir(cwd)
                if not script.AVI.initialized:
                    if prompt:
                        self.HidePreviewWindow()
                        s1 = _('Error loading AviSynth!')
                        s2 = _(
                            'Make sure you have AviSynth installed and that there are no '
                            'unstable plugins or avsi files in the AviSynth plugins directory.'
                        )
                        s2 = '\n'.join(textwrap.wrap(s2, 70))
                        wx.MessageBox('%s\n\n%s' % (s1, s2), _('Error'), style=wx.OK|wx.ICON_ERROR)
                    script.AVI = None
                    return None
                if not self.zoomwindow:
                    script.zoomwindow_actualsize = None
                    if boolOldAVI and (oldWidth, oldHeight) != (script.AVI.Width, script.AVI.Height):
                        script.lastSplitVideoPos = None
                else:
                    #~ script.zoomwindow_actualsize = (script.AVI.WidthActual, script.AVI.HeightActual)
                    script.zoomwindow_actualsize = None
                # Update the script tag properties
                self.UpdateScriptTagProperties(script, scripttxt)
                self.GetAutoSliderInfo(script, scripttxt)
                boolNewAVI = True
            if script == self.currentScript:
                self.refreshAVI = False
        return boolNewAVI

    def UpdateScriptTagProperties(self, script, scripttxt=None):
        if scripttxt is None:
            scripttxt = script.GetText()
        # First strip out comments from scripttxt
        scripttxt = re.sub(r'#.*?\n', r'\n', '%s\n' % scripttxt)
        # Get the toggle tag info
        script.toggleTags = self.GetScriptToggleTagProperties(scripttxt, stripComments=False)
        # Get the slider info
        script.sliderTexts, script.sliderProperties = self.GetScriptSliderProperties(scripttxt, stripComments=False)
        if script.AVI.IsErrorClip():
            script.toggleTags = []
            script.sliderProperties = []
            script.sliderTexts = []

    def GetAutoSliderInfo(self, script, scripttxt=None):
        script.OnStyleNeeded(None, forceAll=True)
        autoSliderInfo = []
        if script.AVI.IsErrorClip() or not self.options['autoslideron']:
            script.autoSliderInfo = []
            return
        nameDict = {}
        posA = posB = 0
        lastpos = script.GetTextLength()
        while posB < lastpos:
            posB = script.WordEndPosition(posA, 1)
            word = script.GetTextRange(posA, posB)
            #~ if word.lower() in script.keywords:
            if script.GetStyleAt(posA) in script.keywordStyleList:
                filterInfo = self.GetFilterArgMatchedInfo(script, posA)
                if filterInfo is not None:
                    wordlower = word.lower()
                    if not wordlower in nameDict:
                        nameDict[wordlower] = 1
                        filterName = word
                    else:
                        nameDict[wordlower] += 1
                        filterName = '%s (%i)' % (word, nameDict[wordlower])
                    if filterInfo:
                        autoSliderInfo.append((filterName,filterInfo))
            posA = posB+1
        script.autoSliderInfo = autoSliderInfo

    def GetFilterArgMatchedInfo(self, script, startwordpos):
        filterMatchedArgs = script.GetFilterMatchedArgs(startwordpos)
        returnInfo = []
        for index, info in enumerate(filterMatchedArgs):
            calltipIndex, calltipArgEntry, argname, argvalue = info
            if argvalue.count(self.sliderOpenString) > 0:
                continue
            if not calltipArgEntry:
                return []
            if not argname:
                argname = None
            returnInfo.append((calltipArgEntry, argname, argvalue, index))
        return returnInfo

    def GetScriptSliderProperties(self, scripttxt, stripComments=True):
        # First strip out comments from scripttxt
        if stripComments:
            scripttxt = re.sub(r'#.*?\n', r'\n', '%s\n' % scripttxt)
        # Then strip out toggle tags
        scripttxt = self.cleanToggleTags(scripttxt)
        # Then find any user sliders
        sliderTexts = self.regexp.findall(scripttxt)
        sliderProperties = []
        for text in sliderTexts:
            items = [s.strip() for s in text.lstrip(self.sliderOpenString).rstrip(self.sliderCloseString).split(',')]
            if len(items) == 4:
                info = (items[0], items[1], items[2])
            else:
                info = None
            sliderProperties.append(info)
        return sliderTexts, sliderProperties

    def GetScriptToggleTagProperties(self, scripttxt, stripComments=True):
        # First strip out comments from scripttxt
        if stripComments:
            scripttxt = re.sub(r'#.*?\n', r'\n', '%s\n' % scripttxt)
        # Then find any toggle tags
        toggleTags = []
        for endtag in re.findall('\[/.*?\]', scripttxt):
            tagname = endtag[2:-1]
            #~ expr = re.compile('\[%s(\s*=.*?)*?\].*?\[/%s\]' % (tagname, tagname), re.IGNORECASE|re.DOTALL)
            expr = re.compile('\[%s.*?\].*?\[/%s\]' % (tagname, tagname), re.IGNORECASE|re.DOTALL)
            try:
                txt = expr.findall(scripttxt)[0]
                toggleTags.append((tagname, self.boolToggleTag(txt)))
            except IndexError:
                pass
        return toggleTags

    def MakePreviewScriptFile(self, script): #, actualsize=None, importname=None):
        # Construct the filename of the temporary avisynth script
        if script.filename:
            dirname = os.path.dirname(script.filename)
        elif os.path.exists(self.options['recentdir']):
            dirname = self.options['recentdir']
        else:
            dirname = self.programdir
        previewname = os.path.join(dirname, 'preview.avs')
        i = 1
        while os.path.exists(previewname):
            previewname = os.path.join(dirname, 'preview%i.avs' % i)
            i = i+1
        # Make sure directory is not read-only
        if not os.access(os.path.dirname(previewname), os.W_OK):
            previewname = os.path.join(self.programdir, 'preview.avs')
        # Get the text to write to the file
        newScripttxt =  self.getCleanText(script.GetText()) #self.regexp.sub(self.re_replace, script.GetText())
        # Write the file
        try:
            f = open(previewname,'w')
            f.write(newScripttxt)
            f.close()
        except UnicodeEncodeError:
            #~ f = codecs.open(previewname, 'w', encoding)
            f.write(newScripttxt.encode(encoding))
            f.close()
        return previewname
        
    def GetFitWindowSize(self):
        h = w = None
        wA, hA = self.videoWindow.GetSize()
        w = wA - 2 * self.xo
        if self.separatevideowindow:
            h = hA - 2 * self.yo
        elif self.zoomwindowfit and not self.previewWindowVisible:
            h = None
            w = None
        else:
            if self.previewWindowVisible:
                splitpos = self.mainSplitter.GetSashPosition() - self.mainSplitter.GetClientSize()[1]
            elif self.currentScript.lastSplitVideoPos is not None:
                splitpos = self.currentScript.lastSplitVideoPos
            elif self.oldLastSplitVideoPos is not None:
                splitpos = self.oldLastSplitVideoPos
            else:
                splitpos = self.GetMainSplitterNegativePosition()
            #~ if self.zoomwindowfit:
                #~ if self.previewWindowVisible:
                    #~ splitpos = self.mainSplitter.GetSashPosition() - self.mainSplitter.GetClientSize()[1]
                #~ else:
                    #~ if self.oldLastSplitVideoPos is not None:
                        #~ splitpos = self.oldLastSplitVideoPos
                    #~ else:
                        #~ splitpos = self.GetMainSplitterNegativePosition()
            #~ elif self.currentScript.lastSplitVideoPos is None:
                #~ splitpos = self.mainSplitter.GetSashPosition() - self.mainSplitter.GetClientSize()[1]
            #~ else:
                #~ splitpos = self.currentScript.lastSplitVideoPos
            h = abs(splitpos) - (2 * self.yo + 5 + self.mainSplitter.GetSashSize()/2)
        if h < 4:
            h = None
        if w < 4:
            w = None
        return (w, h)

    def PaintAVIFrame(self, inputdc, script, frame, shift=True, isPaintEvent=False):
        if script.AVI is None:
            if __debug__:
                print>>sys.stderr, 'Error in PaintAVIFrame: script is None'
            return
        if self.zoomwindow or self.zoomfactor != 1 or self.flip:
            try: # DoPrepareDC causes NameError in wx2.9.1 and fixed in wx2.9.2
                self.videoWindow.DoPrepareDC(inputdc)
            except: 
                self.videoWindow.PrepareDC(inputdc)
            if (self.zoomwindow or self.zoomfactor != 1) and self.flip:
                inputdc.SetBrush(wx.RED_BRUSH)
            elif self.flip:
                inputdc.SetBrush(wx.CYAN_BRUSH)
            inputdc.DrawPolygon([wx.Point(0,0), wx.Point(8,0), wx.Point(0,8)])
        if shift:
            inputdc.SetDeviceOrigin(self.xo, self.yo)
        if self.zoomfactor == 1 and not self.flip and not self.zoomwindow:            
            w = script.AVI.Width
            h = script.AVI.Height
            if self.cropDialog.IsShown() or self.trimDialog.IsShown():
                dc = wx.MemoryDC()
                bmp = wx.EmptyBitmap(w,h)
                dc.SelectObject(bmp)
                script.AVI.DrawFrame(frame, dc.GetHDC())
                self.PaintCropRectangles(dc, script)
                self.PaintTrimSelectionMark(dc, script, frame)
                try: # DoPrepareDC causes NameError in wx2.9.1 and fixed in wx2.9.2
                    self.videoWindow.DoPrepareDC(inputdc)
                except:
                    self.videoWindow.PrepareDC(inputdc)
                inputdc.Blit(0, 0, w, h, dc, 0, 0)
            else:
                dc = inputdc
                try: # DoPrepareDC causes NameError in wx2.9.1 and fixed in wx2.9.2
                    self.videoWindow.DoPrepareDC(dc)
                except:
                    self.videoWindow.PrepareDC(dc)
                script.AVI.DrawFrame(frame, dc.GetHDC())
        else:
            dc = wx.MemoryDC()
            w = script.AVI.Width
            h = script.AVI.Height
            if isPaintEvent and self.bmpVideo:
                dc.SelectObject(self.bmpVideo)                    
            else:
                bmp = wx.EmptyBitmap(w,h)
                dc.SelectObject(bmp)
                script.AVI.DrawFrame(frame, dc.GetHDC())
                if self.flip:
                    img = bmp.ConvertToImage()
                    if 'flipvertical' in self.flip:
                        img = img.Mirror(False)
                    if 'fliphorizontal' in self.flip:
                        img = img.Mirror()
                    bmp = wx.BitmapFromImage(img)
                    dc.SelectObject(bmp)
                self.PaintTrimSelectionMark(dc, script, frame)
                #~ self.PaintCropRectangles(dc, script)
                self.bmpVideo = bmp
            try: # DoPrepareDC causes NameError in wx2.9.1 and fixed in wx2.9.2
                self.videoWindow.DoPrepareDC(inputdc)
            except:
                self.videoWindow.PrepareDC(inputdc)
            inputdc.SetUserScale(self.zoomfactor, self.zoomfactor)
            inputdc.Blit(0, 0, w, h, dc, 0, 0)
            if isPaintEvent and self.zoomwindowfill and self.firstToggled:
                wx.CallAfter(self.ShowVideoFrame)
                self.firstToggled = False
        self.paintedframe = frame

    def PaintTrimSelectionMark(self, dc, script, frame):
        if self.trimDialog.IsShown() and self.markFrameInOut:
            boolInside = self.ValueInSliderSelection(frame)
            if boolInside is not None:
                dc.SetLogicalFunction(wx.COPY)
                dc.SetPen(wx.Pen(wx.BLACK, 2))
                if boolInside:
                    dc.SetBrush(wx.GREEN_BRUSH)
                    dc.DrawCircle(25, 25, 20)
                else:
                    #~ dc.SetLogicalFunction(wx.COPY)
                    #~ dc.SetBrush(wx.RED_BRUSH)
                    #~ w = script.AVI.Width
                    #~ h = script.AVI.Height
                    #~ a = w/20
                    #~ b = w/10
                    #~ dc.DrawPolygon([(a,a), (a+b,a), (w-a,h-a), (w-a-b,h-a)])
                    #~ dc.DrawPolygon([(w-a,a), (w-a-b,a), (a,h-a), (a+b,h-a)])
                    dc.SetBrush(wx.RED_BRUSH)
                    dc.DrawCircle(25, 25, 20)

    def PaintCropRectangles(self, dc, script):
        # Paint the trim rectangles
        w = script.AVI.Width
        h = script.AVI.Height
        left = self.cropValues['left']
        top = self.cropValues['top']
        mright = self.cropValues['-right']
        mbottom = self.cropValues['-bottom']
        dc.SetLogicalFunction(wx.INVERT)
        if top > 0:
            dc.DrawRectangle(0, 0, w, top)
        if mbottom > 0:
            dc.DrawRectangle(0, h - mbottom, w, h)
        if left > 0:
            dc.DrawRectangle(0, top, left, h - mbottom - top)
        if mright > 0:
            dc.DrawRectangle(w - mright, top, mright, h - mbottom - top)
        self.oldCropValues = self.cropValues

    def PaintCropWarnings(self, spinCtrl=None):
        script = self.currentScript
        keys = ('left', 'top', '-right', '-bottom')
        if spinCtrl is not None:
            keys = [key for key in keys if self.cropDialog.ctrls[key] == spinCtrl]
        self.cropDialog.boolInvalidCrop = False
        for key in keys:
            labelCtrl = self.cropDialog.ctrls[key+'Label']
            textCtrl = self.cropDialog.ctrls[key]
            value = textCtrl.GetValue()
            if value % 2 and script.AVI.Colorspace.lower() in ('yv12', 'yuy2'):
                #~ textCtrl.SetBackgroundColour('pink')
                labelCtrl.SetForegroundColour('red')
                self.cropDialog.boolInvalidCrop = True
            else:
                #~ textCtrl.SetBackgroundColour(color)
                labelCtrl.SetForegroundColour(wx.NullColour)
            labelCtrl.Refresh()

    def RunExternalPlayer(self, path=None, script=None, args=None, prompt=True):
        if script is None:
            script = self.currentScript
        index = self.scriptNotebook.GetSelection()
        tabTitle = self.scriptNotebook.GetPageText(index)
        if not script.GetModify() and os.path.isfile(script.filename):
            # Always use original script if there are no unsaved changes
            previewname = script.filename
            boolTemp = False
        elif self.options['previewunsavedchanges'] or not os.path.isfile(script.filename):
            previewname = self.MakePreviewScriptFile(script)
            boolTemp = True
        else:
            if self.options['promptwhenpreview']:
                if script.GetModify():
                    dlg = wx.MessageDialog(self, _('Save changes before previewing?'),
                        tabTitle, wx.YES_NO|wx.CANCEL)
                    ID = dlg.ShowModal()
                    dlg.Destroy()
                    if ID == wx.ID_YES:
                        self.SaveScript(script.filename, index)
                    elif ID == wx.ID_CANCEL:
                        pass
            previewname = script.filename
            boolTemp = False
        if path is None:
            path = self.options['externalplayer']
        if args is None:
            args = self.options['externalplayerargs']
        if not os.path.isfile(path):
            if not prompt:
                return False
            filefilter = _('Executable files (*.exe)|*.exe|All files (*.*)|*.*')
            dlg = wx.FileDialog(self, _('Select an external player'), '', '', filefilter, wx.OPEN)
            ID = dlg.ShowModal()
            if ID == wx.ID_OK:
                path = dlg.GetPath()
            else:
                path = ''
            dlg.Destroy()
        if not os.path.isfile(path):
            if path != '':
                wx.MessageBox(_('A program must be specified to use this feature!'), _('Error'), style=wx.OK|wx.ICON_ERROR)
            return
        self.options['externalplayer'] = path
        # Run the process
        process = wx.Process(self)
        def OnEndProcess(event):
            try:
                os.remove(previewname)
            except OSError:
                pass
        #~ process.Bind(wx.EVT_END_PROCESS, lambda event: os.remove(previewname))
        if boolTemp:
            process.Bind(wx.EVT_END_PROCESS, OnEndProcess)
        self.pid = wx.Execute('%s "%s" %s' % (path, previewname, args), wx.EXEC_ASYNC, process)
        return True

    def re_replace(self, mo):
        items = mo.group().lstrip(self.sliderOpenString).rstrip(self.sliderCloseString).split(',')
        if len(items) == 4:
            return items[3].strip()
        elif len(items) == 1:
            return ''
        else:
            return mo.group()

    def re_replace2(self, mo):
        txt = mo.group()
        if self.boolToggleTag(txt):
            posA = txt.find(']') + 1
            posB = txt.rfind('[')
            return txt[posA:posB]
        else:
            return ''

    def boolToggleTag(self, txt):
        starttag = txt[1:txt.find(']')]
        boolKeep = True
        try:
            name, value = starttag.split('=')
            try:
                boolKeep = bool(int(value))
            except ValueError:
                pass
        except ValueError:
            pass
        return boolKeep

    def _x_re_replaceStrip(self, mo):
        return ''.join(re.split('\[.*?\]', mo.group()))

    def createAutoUserSliders(self, script):
        script.sliderWindow.Freeze()
        script.sliderSizerNew.Clear(deleteWindows=True)
        script.sliderToggleLabels = []
        menuInfoGeneral = [
            (_('Edit filter database'), '', self.OnSliderLabelEditDatabase, ''),
            (''),
            (_('Toggle all folds'), '', self.OnSliderLabelToggleAllFolds, ''),
            (_('General settings...'), '', self.OnSliderLabelSettings, ''),
        ]
        menuGeneral = self.createMenu(menuInfoGeneral)
        #~ menuInfoNumberSlider = [
            #~ (_('Modify slider properties'), '', self.OnSliderLabelModifySliderProperties, _('')),
        #~ ] + menuInfoGeneral
        #~ menuNumberSlider = self.createMenu(menuInfoNumberSlider)
        exclusionList = self.options['autosliderexclusions'].lower().split()
        row = 0
        for filterName, filterInfo in script.autoSliderInfo:
            if filterName.lower() in exclusionList:
                continue
            separator = None
            for info, enteredName, enteredValue, argIndex in filterInfo:
                # Parse the argument info entered into the script
                splitEnteredValue = enteredValue.split('=')
                if len(splitEnteredValue) == 2:
                    namedArg, strValue = splitEnteredValue
                else:
                    namedArg = None
                    strValue = enteredValue
                strValue = strValue.strip(string.whitespace+'\\')
                if strValue.startswith(self.sliderOpenString) and strValue.endswith(self.sliderCloseString):
                    continue
                # Parse the calltip info and build the appropriate slider
                argtype, argname, guitype, defaultValue, other = self.ParseCalltipArgInfo(info, strValue=strValue)
                if argtype is None or argname is None or guitype is None or argtype not in ('int', 'float', 'bool', 'string'):
                    continue
                if enteredName is not None:
                    if argname.startswith('"') and argname.endswith('"'):
                        argname = '"%s"' % enteredName.strip('"')
                    else:
                        argname = enteredName
                boolException = False
                if guitype == 'slider':
                    # Create a numerical slider
                    if not self.options['autoslidermakeintfloat']:
                        continue
                    minValue, maxValue, nDecimal, mod = other
                    try:
                        value = float(strValue)
                    except ValueError:
                        boolException = True
                        value = None
                    if value is None:
                        value = minValue
                    if value < minValue:
                        minValue = value
                    if value > maxValue:
                        maxValue = value
                    if separator is None:
                        separator = self.addAvsSliderSeparatorNew(script, label=filterName, menu=menuGeneral, row=row, sizer=script.sliderSizerNew)
                        row += 1
                    if boolException:
                        self.addAvsGenericArg(script, argname, strValue, row, separator, filterName, argIndex)
                    else:
                        self.addAvsSliderNew(script, argname, value, minValue, maxValue, defaultValue, nDecimal, mod, row, sizer=script.sliderSizerNew, separator=separator, filterName=filterName, argIndex=argIndex)
                    row += 1
                elif guitype == 'color':
                    # Create a color picker button
                    if not self.options['autoslidermakecolor']:
                        continue
                    if strValue.startswith('$'):
                        try:
                            value = strValue.split('$', 1)[1]
                            int(value, 16)
                        except ValueError:
                            boolException = True
                    else:
                        try:
                            value = '%X' % int(strValue)
                            if len(value) <= 6:
                                value = value.rjust(6, '0')
                            else:
                                boolException = True
                        except ValueError:
                            boolException = True
                    if separator is None:
                        separator = self.addAvsSliderSeparatorNew(script, label=filterName, menu=menuGeneral, row=row, sizer=script.sliderSizerNew)
                        row += 1
                    if boolException:
                        self.addAvsGenericArg(script, argname, strValue, row, separator, filterName, argIndex)
                    else:
                        self.addAvsColorPicker(script, argname, value, defaultValue, row, separator, filterName, argIndex)
                    row += 1
                elif guitype == 'boolradio':
                    # Create a true/false radio box
                    if not self.options['autoslidermakebool']:
                        continue
                    if strValue.lower() in ('true', 'false'):
                        if strValue.lower() == 'true':
                            value = True
                        else:
                            value = False
                    else:
                        boolException = True
                    if separator is None:
                        separator = self.addAvsSliderSeparatorNew(script, label=filterName, menu=menuGeneral, row=row, sizer=script.sliderSizerNew)
                        row += 1
                    if boolException:
                        self.addAvsGenericArg(script, argname, strValue, row, separator, filterName, argIndex)
                    else:
                        self.addAvsBooleanRadio(script, argname, value, defaultValue, row, separator, filterName, argIndex)
                    row += 1
                elif guitype == 'stringlist':
                    if not self.options['autoslidermakestringlist']:
                        continue
                    choices = other
                    if not strValue.startswith('"') or not strValue.endswith('"'):
                        boolException = True
                    else:
                        value = strValue.strip('"')
                    if separator is None:
                        separator = self.addAvsSliderSeparatorNew(script, label=filterName, menu=menuGeneral, row=row, sizer=script.sliderSizerNew)
                        row += 1
                    if boolException:
                        self.addAvsGenericArg(script, argname, strValue, row, separator, filterName, argIndex)
                    else:
                        self.addAvsStringChoice(script, argname, value, choices, defaultValue, row, separator, filterName, argIndex)
                    row += 1
                elif guitype == 'stringfilename':
                    if not self.options['autoslidermakestringfilename']:
                        continue
                    extList = other
                    if not strValue.startswith('"') or not strValue.endswith('"'):
                        boolException = True
                    else:
                        value = strValue.strip('"')
                    if separator is None:
                        separator = self.addAvsSliderSeparatorNew(script, label=filterName, menu=menuGeneral, row=row, sizer=script.sliderSizerNew)
                        row += 1
                    if boolException:
                        self.addAvsGenericArg(script, argname, strValue, row, separator, filterName, argIndex)
                    else:
                        self.addAvsFilenamePicker(script, argname, value, extList, row, separator, filterName, argIndex)
                    row += 1
                elif guitype in ('undocumented', 'error'):
                    # Undocumented argument
                    if not self.options['autoslidermakeunknown']:
                        continue
                    if separator is None:
                        separator = self.addAvsSliderSeparatorNew(script, label=filterName, menu=menuGeneral, row=row, sizer=script.sliderSizerNew)
                        row += 1
                    self.addAvsGenericArg(script, argname, strValue, row, separator, filterName, argIndex)
                    row += 1
        if row == 0:
            script.autoSliderInfo = []
        else:
            # Add a spacer
            height = 0
            if script.sliderTexts != []:
                height = 20
            script.sliderSizerNew.Add((5, height), (row, 7))
        if wx.VERSION > (2, 9):
            script.sliderSizerNew.Add((0, 0), (row, 3))
            if not script.sliderSizerNew.IsColGrowable(3):
                script.sliderSizerNew.AddGrowableCol(3)
        # Fold according to user set preference
        foldLevel = self.options['autosliderstartfold']
        if foldLevel == 0:
            # Fold all filters
            for item in script.sliderToggleLabels:
                self.ToggleSliderFold(item, fold=True, refresh=False)
            self.foldAllSliders = False
        elif foldLevel == 1:
            # Fold none, don't need to do anything
            self.foldAllSliders = True
        elif foldLevel == 2:
            # Fold only filters without numerical sliders
            boolAnyUnfolded = False
            for item in script.sliderToggleLabels:
                if not item.hasNumericalSlider:
                    self.ToggleSliderFold(item, fold=True, refresh=False)
                else:
                    boolAnyUnfolded = True
            if boolAnyUnfolded:
                self.foldAllSliders = True
        else:
            pass
        script.sliderWindow.Thaw()

    def ParseCalltipArgInfo(self, info, strValue=None):
        # TODO: handle repeating args [, ...]
        info = re.sub(r'\[.*\]', '', info)
        argtypename = info.split('=', 1)[0].strip()
        splitargtypename = argtypename.split()
        if len(splitargtypename) != 2:
            if len(splitargtypename) == 1:
                return (argtypename.lower(), None, None, None, None)
            else:
                return (None, None, None, None, None)
        argtype, argname = splitargtypename
        argtype = argtype.lower()
        if info.count('=') > 0:
            argInfo = info.split('=', 1)[1].strip()
            splitargtypename = argtypename.split()
            if argtype in ('float', 'int'):
                defaultValue = minValue = maxValue = nDecimal = mod = None
                strDefaultValue = strMinValue = strMaxValue = strStepSize = ''
                splitargInfo = argInfo.split('(',1)
                if len(splitargInfo) == 1:
                    strDefaultValue = argInfo
                    if strDefaultValue.startswith('$'):
                        try:
                            hexstring = strDefaultValue.split('$', 1)[1]
                            int(hexstring, 16)
                            return (argtype, argname, 'color', hexstring, None)
                        except ValueError:
                            return (argtype, argname, 'error', strDefaultValue, None)
                    else:
                        if argtype == 'int':
                            try:
                                defaultValue = int(strDefaultValue)
                                nDecimal = 0
                            except ValueError:
                                defaultValue = strDefaultValue
                        elif argtype == 'float':
                            try:
                                defaultValue = float(strDefaultValue)
                                splitStrvalue = strDefaultValue.split('.')
                                if len(splitStrvalue) == 2:
                                    nDecimal = len(splitStrvalue[1].strip())
                                else:
                                    nDecimal = 0
                            except ValueError:
                                defaultValue = strDefaultValue
                        return (argtype, argname, 'error', defaultValue, (minValue, maxValue, nDecimal, mod))
                elif len(splitargInfo) == 2:
                    strDefaultValue, rest = splitargInfo
                    strDefaultValue = strDefaultValue.strip()
                    boolValueError = False
                    try:
                        defaultValue = float(strDefaultValue)
                    except ValueError:
                        if strDefaultValue.startswith('$'):
                            try:
                                hexstring = strDefaultValue.split('$', 1)[1]
                                int(hexstring, 16)
                                return (argtype, argname, 'color', hexstring, None)
                            except ValueError:
                                return (argtype, argname, 'error', None, None)
                        else:
                            try:
                                defaultValue = float(strValue)
                                strDefaultValue = strValue
                            except:
                                defaultValue = None
                                #~ strDefaultValue = ''
                    splitrest = rest.split(')', 1)
                    if len(splitrest) == 2:
                        rangeInfo, extra = splitrest
                    else:
                        rangeInfo = rest
                        extra = ''
                    splitrangeInfo = rangeInfo.split(' to ')
                    if len(splitrangeInfo) == 2:
                        strMinValue, restRangeInfo = [s.strip() for s in splitrangeInfo]
                        try:
                            minValue = float(strMinValue)
                        except ValueError:
                            #~ return (argtype, argname, 'error', None, None)
                            #~ return (argtype, argname, 'error', strDefaultValue, (strMinValue, strMaxValue, 0, strStepSize))
                            boolValueError = True
                        splitrestRangeInfo = restRangeInfo.split(' by ')
                        if len(splitrestRangeInfo) == 2:
                            strMaxValue, strStepSize = [s.strip() for s in splitrestRangeInfo]
                        else:
                            strMaxValue = restRangeInfo.strip()
                            strStepSize = None
                        try:
                            maxValue = float(strMaxValue)
                        except ValueError:
                            #~ return (argtype, argname, 'error', None, None)
                            #~ return (argtype, argname, 'error', strDefaultValue, (strMinValue, strMaxValue, 0, strStepSize))
                            boolValueError = True
                        if argtype == 'int':
                            nDecimal = 0
                        if strStepSize is None and not boolValueError:
                            strStepSize = ''
                            # Get the step size from the strDefaultValue, strMinValue, strMaxValue
                            nDecimals = []
                            for eachValue in (strDefaultValue, strMinValue, strMaxValue):
                                splitStrvalue = eachValue.split('.')
                                if len(splitStrvalue) == 2:
                                    nDecimal = len(splitStrvalue[1].strip())
                                else:
                                    nDecimal = 0
                                nDecimals.append(nDecimal)
                            nDecimal = max(nDecimals)
                        elif not boolValueError:
                            try:
                                stepSize = float(strStepSize)
                                if stepSize > 1.0:
                                    nDecimal = 0
                                    mod = int(stepSize)
                                else:
                                    try:
                                        nDecimal = len(strStepSize.split('.')[1].strip())
                                    except IndexError:
                                        nDecimal = 0
                                        mod = None
                            except ValueError:
                                #~ return (argtype, argname, 'error', None, None)
                                #~ return (argtype, argname, 'error', strDefaultValue, (strMinValue, strMaxValue, 0, strStepSize))
                                boolValueError = True
                    if boolValueError:
                        return (argtype, argname, 'error', strDefaultValue, (strMinValue, strMaxValue, 0, strStepSize))
                errType, errMsg, sliderValues = self.ValidateAvsSliderInputs(strDefaultValue, strMinValue, strMaxValue, strStepSize)
                if errType is not None:
                    #~ return (argtype, argname, 'error', None, None)
                    return (argtype, argname, 'error', strDefaultValue, (strMinValue, strMaxValue, 0, strStepSize))
                if None in (defaultValue, minValue, maxValue, nDecimal):
                    return (argtype, argname, 'error', strDefaultValue, (strMinValue, strMaxValue, 0, strStepSize))
                if argtype == 'int':
                    defaultValue = int(defaultValue)
                    minValue = int(minValue)
                    maxValue = int(maxValue)
                return (argtype, argname, 'slider', defaultValue, (minValue, maxValue, nDecimal, mod))
            elif argtype == 'bool':
                defaultValue = argInfo.strip()
                if defaultValue.lower() in ('true', 'false'):
                    return (argtype, argname, 'boolradio', defaultValue, None)
                else:
                    return (argtype, argname, 'error', defaultValue, None)
            elif argtype == 'string':
                splitargInfo = argInfo.split('(',1)
                defaultValue = None
                if len(splitargInfo) == 2:
                    strDefaultValue, rest = splitargInfo
                    defaultValue = strDefaultValue.strip()
                    if defaultValue:
                        defaultValue = '"%s"' % defaultValue.strip('"')
                    choices = ['"%s"' % s.strip(' "') for s in rest.split(')')[0].split('/')]
                else:
                    return (argtype, argname, 'error', argInfo.strip(), None)
                #~ if argInfo.count('*.') > 0:
                if '/'.join(choices).count('*.') > 0:
                    # Filename selector
                    #~ extList = [s.strip(' "') for s in argInfo.split('(',1)[0].split('/') if s.strip(' "').startswith('*.')]
                    extList = [s.strip('"') for s in choices if s.strip('"').startswith('*.')]
                    return (argtype, argname, 'stringfilename', defaultValue, extList)
                else:
                    #~ # String list
                    #~ splitargInfo = argInfo.split('(',1)
                    #~ if len(splitargInfo) == 2:
                        #~ strDefaultValue, rest = splitargInfo
                        #~ defaultValue = strDefaultValue.strip(' "')
                        #~ choices = [s.strip(' "') for s in rest.split(')')[0].split('/')]
                    #~ else:
                        #~ return (argtype, argname, 'error', None, None)
                    return (argtype, argname, 'stringlist', defaultValue, choices)
            else:
                return (argtype, argname, 'clip', None, None)
        else:
            # No database info
            if argtype == 'bool':
                return (argtype, argname, 'boolradio', None, None)
            return (argtype, argname, 'undocumented', None, None)

    def createUserSliders(self, script, parseonly=False):
        sliderTexts = script.sliderTexts
        # Parse the slider texts
        labels = []
        argsList = []
        for text in sliderTexts:
            items = [s.strip() for s in text.lstrip(self.sliderOpenString).rstrip(self.sliderCloseString).split(',')]
            if len(items) != 4:
                if len(items) == 1:
                    splititem = items[0].split('=',1)
                    if len(splititem) == 2:
                        argsList.append([splititem[1].strip('"')])
                    else:
                        argsList.append([''])
                continue
            minValue = maxValue = value = None
            try:
                # Store the items
                label = items[0].strip(''' "' ''')#strip('"').strip("'")
                minValue = float(items[1])
                maxValue = float(items[2])
                value = float(items[3])
                if minValue >= maxValue:
                    #~ print>>sys.stderr, _('Error: invalid slider text:'), text
                    #~ continue
                    self.displaySliderWarning(script, text, items[1], _('Invalid slider text: min > max'))
                    return False
                if value < minValue or value > maxValue:
                    #~ print>>sys.stderr, _('Error: invalid slider text:'), text
                    #~ continue
                    self.displaySliderWarning(script, text, items[3], _('Invalid slider text: value not in bounds'))
                    return False
                # Get the number of decimals (to determine slider increments)
                nDecimal = 0
                items = [s.strip() for s in text.lstrip(self.sliderOpenString).rstrip(self.sliderCloseString).split(',')]
                for strnum in items[1:]:
                    strsplit = strnum.split('.')
                    if len(strsplit) == 2:
                        n = len(strsplit[1])
                    else:
                        n = 0
                    if n > nDecimal:
                        nDecimal = n
                # Get the modulo (slider step size)
                mod = None
                splitlabel = label.split('%', 1)
                if len(splitlabel) == 2:
                    try:
                        mod = int(splitlabel[1])
                    except ValueError:
                        #~ print>>sys.stderr, _('Error: invalid slider text:'), text
                        #~ continue
                        self.displaySliderWarning(script, text, splitlabel[1].strip(), _('Invalid slider text: bad modulo label'))
                        return False
                if mod is not None:
                    #~ tempMinValue = minValue + minValue % mod
                    #~ tempMaxValue = maxValue - maxValue % mod
                    if mod == 0:
                        mod = None
                    else:
                        invalidNumber = False
                        if (int(value) - int(minValue)) % mod != 0 or (int(maxValue) - int(minValue)) % mod != 0:
                            invalidNumber = True
                        if invalidNumber or mod > maxValue - minValue:
                            mod = None
                    if mod is not None:
                        nDecimal = 0
                        minValue = int(minValue) #tempMinValue
                        maxValue = int(maxValue) #tempMaxValue
                        value = int(value) #min(value + value % mod, maxValue)
                if label not in labels:
                    #~ self.addAvsSlider(script, label, minValue, maxValue, value, nDecimal, mod)
                    argsList.append((script, label, minValue, maxValue, value, nDecimal, mod))
                    labels.append(label)
                else:
                    #~ print>>sys.stderr, _('Error: User slider %(label)s already exists!') % locals()
                    self.displaySliderWarning(script, text, label, _('Invalid slider text: slider label already exists'))
                    return False
            except ValueError:
                #~ print>>sys.stderr, _('Error: invalid slider text:'), text
                #~ continue
                if minValue is None:
                    highlightText = items[1]
                elif maxValue is None:
                    highlightText = items[2]
                elif value is None:
                    highlightText = items[3]
                else:
                    highlightText = items[0]
                self.displaySliderWarning(script, text, highlightText, _('Invalid slider text: invalid number'))
                return False
        if parseonly:
            parsedInfo = [arg[1:] for arg in argsList]
            return zip(sliderTexts, parsedInfo)
        # Create the new sliders
        script.sliderSizer.Clear(deleteWindows=True)
        for row, args in enumerate(argsList):
            if len(args) == 1:
                self.addAvsSliderSeparator(script, label=args[0], row=row)
            else:
                args = args + (row,)
                self.addAvsSlider(*args)
        if wx.VERSION > (2, 9):
            script.sliderSizer.Add((0, 0), (len(argsList), 3))
            if not script.sliderSizer.IsColGrowable(3):
                script.sliderSizer.AddGrowableCol(3)
        return True

    def displaySliderWarning(self, script, sliderText, highlightText, msg):
        pos = script.FindText(0, script.GetTextLength(), sliderText)
        posA = script.FindText(pos, script.GetTextLength(), highlightText, stc.STC_FIND_WHOLEWORD)
        posB = posA + len(highlightText)
        script.SetSelection(posA, posB)
        script.SetFocus()
        wx.MessageBox(msg, _('Warning'))

    def addAvsSlider(self, script, labelTxt, minValue, maxValue, value, nDecimal, mod=None, row=None, sizer=None):
        if minValue is None or maxValue is None or value is None or nDecimal is None:
            return
        if sizer is None:
            sizer = script.sliderSizer
        parent = script.sliderWindow
        isRescaled = False
        if mod:            
            m = re.search(r'([\d.+-]+)%', labelTxt)
            try:
                minValue2 = int(m.group(1))
                isRescaled = True
            except:
                self.IdleCall.append((wx.MessageBox, (_('Invalid slider tag for rescaling!\nAccept only +, -, or an integer.'), _('Warning'), wx.OK|wx.ICON_EXCLAMATION, self), {})) 
        elif labelTxt[-1] == '+':
            minValue2 = 0
            mod = (maxValue - minValue) / 100.
            isRescaled = True
        elif labelTxt[-1] == '-':
            minValue2 = -100
            mod = (maxValue - minValue) / 200.
            isRescaled = True
        if isRescaled:
            def Rescale(val):
                return minValue2 + (val - minValue)/mod
        # Construct the format string based on nDecimal
        strTemplate = '%.'+str(nDecimal)+'f'
        strTemplate2 = '(%.'+str(nDecimal)+'f)'
        def OnScroll(event):
            value = slider.GetValue()
            valTxtCtrl.SetLabel(strTemplate % value)
            if isRescaled:
                valTxtCtrl2.SetLabel(strTemplate2 % Rescale(value))
        # Create the slider
        slider = wxp.Slider(parent, wx.ID_ANY,
            value, minValue, maxValue,
            size=(50,-1),
            style=wx.SL_BOTH,
            name=labelTxt,
            nDecimal=nDecimal,
            mod=mod,
            #~ onscroll= lambda event: valTxtCtrl.SetLabel(strTemplate % slider.GetValue())
            onscroll = OnScroll,
        )
        # Slider event binding
        slider.Bind(wx.EVT_LEFT_UP, self.OnLeftUpUserSlider)
        # Create the static text labels
        labelTxtCtrl = wx.StaticText(parent, wx.ID_ANY, labelTxt)
        minTxtCtrl = wx.StaticText(parent, wx.ID_ANY, strTemplate % minValue)
        maxTxtCtrl = wx.StaticText(parent, wx.ID_ANY, strTemplate % maxValue)
        valTxtCtrl = wx.StaticText(parent, wx.ID_ANY, strTemplate % value)
        valTxtCtrl.SetForegroundColour(wx.BLUE)
        valTxtCtrl.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        value_formatted = strTemplate % value
        valTxtCtrl.SetToolTip(wx.ToolTip(_('Reset to initial value: %(value_formatted)s') % locals()))
        if isRescaled:
            minTxtCtrl2 = wx.StaticText(parent, wx.ID_ANY, strTemplate2 % minValue2)
            minTxtCtrlSizer = wx.BoxSizer(wx.VERTICAL)
            minTxtCtrlSizer.Add(minTxtCtrl, 0, wx.ALIGN_CENTER)
            minTxtCtrlSizer.Add(minTxtCtrl2, 0, wx.ALIGN_CENTER)
            maxTxtCtrl2 = wx.StaticText(parent, wx.ID_ANY, strTemplate2 % Rescale(maxValue))
            maxTxtCtrlSizer = wx.BoxSizer(wx.VERTICAL)
            maxTxtCtrlSizer.Add(maxTxtCtrl, 0, wx.ALIGN_CENTER)
            maxTxtCtrlSizer.Add(maxTxtCtrl2, 0, wx.ALIGN_CENTER)
            value2_formatted = strTemplate2 % Rescale(value)
            valTxtCtrl2 = wx.StaticText(parent, wx.ID_ANY, value2_formatted)
            valTxtCtrlSizer = wx.BoxSizer(wx.VERTICAL)
            valTxtCtrlSizer.Add(valTxtCtrl, 0, wx.EXPAND)
            valTxtCtrlSizer.Add(valTxtCtrl2, 0, wx.EXPAND)
            valTxtCtrl2.SetForegroundColour(wx.RED)
            valTxtCtrl2.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
            valTxtCtrl2.SetToolTip(wx.ToolTip(_('Reset to initial value: %(value2_formatted)s') % locals()))
        def OnTextLeftDown(event):
            valTxtCtrl.SetLabel(value_formatted)
            if isRescaled:
                valTxtCtrl2.SetLabel(value2_formatted)
            slider.SetValue(value)
            self.UserSliderVideoUpdate(slider)
        valTxtCtrl.Bind(wx.EVT_LEFT_DOWN, OnTextLeftDown)
        if isRescaled:
            valTxtCtrl2.Bind(wx.EVT_LEFT_DOWN, OnTextLeftDown)
        #~ leftCtrl = wxButtons.GenButton(parent, wx.ID_ANY, '<', size=(16,16))
        leftCtrl = wxButtons.GenBitmapButton(parent, wx.ID_ANY, self.bmpLeftTriangle, size=(16,16))
        leftCtrl.SetBezelWidth(1)
        leftCtrl.SetUseFocusIndicator(False)
        #~ leftCtrl.SetToolTip(wx.ToolTip('Decrement slider'))
        #~ def OnButtonLeftIncrement(event):
            #~ newvalue = slider.Decrement()
            #~ valTxtCtrl.SetLabel(strTemplate % newvalue)
            #~ self.UserSliderVideoUpdate(slider)
        #~ parent.Bind(wx.EVT_BUTTON, OnButtonLeftIncrement, leftCtrl)
        def OnLeftTimer(event):
            newvalue = slider.Decrement()
            valTxtCtrl.SetLabel(strTemplate % newvalue)
            if isRescaled:
                valTxtCtrl2.SetLabel(strTemplate2 % Rescale(newvalue))
            if leftCtrl.up:
                leftTimer.Stop()
                self.UserSliderVideoUpdate(slider)
                if leftCtrl.HasCapture():
                    leftCtrl.ReleaseMouse()
            event.Skip()
        leftTimer = wx.Timer(leftCtrl)
        leftCtrl.Bind(wx.EVT_TIMER, OnLeftTimer)
        def OnButtonDecLeftDown(event):
            newvalue = slider.Decrement()
            valTxtCtrl.SetLabel(strTemplate % newvalue)
            if isRescaled:
                valTxtCtrl2.SetLabel(strTemplate2 % Rescale(newvalue))
            self.fc = wx.FutureCall(300, leftTimer.Start, 100)
            #~ leftTimer.Start(100)
            event.Skip()
        def OnButtonDecLeftUp(event):
            if self.fc is not None:
                self.fc.Stop()
            leftTimer.Stop()
            self.UserSliderVideoUpdate(slider)
            event.Skip()
        leftCtrl.Bind(wx.EVT_LEFT_DOWN, OnButtonDecLeftDown)
        leftCtrl.Bind(wx.EVT_LEFT_UP, OnButtonDecLeftUp)
        #~ rightCtrl = wxButtons.GenButton(parent, wx.ID_ANY, '>', size=(16,16))
        rightCtrl = wxButtons.GenBitmapButton(parent, wx.ID_ANY, self.bmpRightTriangle, size=(16,16))
        rightCtrl.SetBezelWidth(1)
        rightCtrl.SetUseFocusIndicator(False)
        #~ def OnButtonRightIncrement(event):
            #~ newvalue = slider.Increment()
            #~ valTxtCtrl.SetLabel(strTemplate % newvalue)
            #~ self.UserSliderVideoUpdate(slider)
        #~ parent.Bind(wx.EVT_BUTTON, OnButtonRightIncrement, rightCtrl)
        def OnRightTimer(event):
            newvalue = slider.Increment()
            valTxtCtrl.SetLabel(strTemplate % newvalue)
            if isRescaled:
                valTxtCtrl2.SetLabel(strTemplate2 % Rescale(newvalue))
            if rightCtrl.up:
                rightTimer.Stop()
                self.UserSliderVideoUpdate(slider)
                if rightCtrl.HasCapture():
                    rightCtrl.ReleaseMouse()
            event.Skip()
        rightTimer = wx.Timer(rightCtrl)
        rightCtrl.Bind(wx.EVT_TIMER, OnRightTimer)
        def OnButtonIncLeftDown(event):
            newvalue = slider.Increment()
            valTxtCtrl.SetLabel(strTemplate % newvalue)
            if isRescaled:
                valTxtCtrl2.SetLabel(strTemplate2 % Rescale(newvalue))
            self.fc = wx.FutureCall(300, rightTimer.Start, 100)
            #~ rightTimer.Start(100)
            event.Skip()
        def OnButtonIncLeftUp(event):
            if self.fc is not None:
                self.fc.Stop()
            rightTimer.Stop()
            self.UserSliderVideoUpdate(slider)
            event.Skip()
        rightCtrl.Bind(wx.EVT_LEFT_DOWN, OnButtonIncLeftDown)
        rightCtrl.Bind(wx.EVT_LEFT_UP, OnButtonIncLeftUp)
        # Add the elements to the sliderSizer
        sizer.Add(labelTxtCtrl, (row,0), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        if isRescaled:
            sizer.Add(minTxtCtrlSizer, (row,1), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        else:
            sizer.Add(minTxtCtrl, (row,1), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        sizer.Add(leftCtrl, (row,2), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 5)
        sizer.Add(slider, (row,3), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)
        sizer.Add(rightCtrl, (row,4), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        if isRescaled:
            sizer.Add(maxTxtCtrlSizer, (row,5), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
            sizer.Add(valTxtCtrlSizer, (row,6), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 0)
        else:
            sizer.Add(maxTxtCtrl, (row,5), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
            sizer.Add(valTxtCtrl, (row,6), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 0)
        #sizer.Add((10, -1), (row,7))

        #~ script.sliderSizer.Layout()
        #~ slider.Refresh()

    def addAvsSliderSeparator(self, script, label='', row=None, sizer=None):
        if sizer is None:
            sizer = script.sliderSizer
        parent = script.sliderWindow
        color1 = wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DSHADOW)
        color2 = wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DHILIGHT)
        # Add a separator
        tempsizer = wx.BoxSizer(wx.VERTICAL)
        if row == 0: border = 0
        else: border = 10
        if label == '':
            tempsizer.Add(wx.StaticLine(parent), 0, wx.EXPAND|wx.ALIGN_BOTTOM|wx.TOP, border)
        else:
            staticText = wx.StaticText(parent, wx.ID_ANY, label)
            font = staticText.GetFont()
            font.SetWeight(wx.FONTWEIGHT_BOLD)
            staticText.SetFont(font)
            tempsizer.Add(staticText, 0, wx.ALIGN_BOTTOM|wx.TOP, border)
            tempsizer.Add(wx.StaticLine(parent), 0, wx.EXPAND|wx.ALIGN_BOTTOM)
        sizer.Add(tempsizer, (row,0), (1,7), wx.EXPAND)

    def addAvsSliderNew(self, script, labelTxt, value, minValue, maxValue, defaultValue, nDecimal, mod=None, row=None, sizer=None, separator=None, filterName=None, argIndex=None):
        if minValue is None or maxValue is None or value is None or nDecimal is None:
            return
        if sizer is None:
            sizer = script.sliderSizer
        parent = script.sliderWindow
        # Construct the format string based on nDecimal
        strTemplate = '%.'+str(nDecimal)+'f'
        # Create the slider
        slider = wxp.Slider(parent, wx.ID_ANY,
            value, minValue, maxValue,
            size=(50,-1),
            style=wx.SL_BOTH,
            name=labelTxt,
            nDecimal=nDecimal,
            mod=mod,
            onscroll= lambda event: valTxtCtrl.SetLabel(strTemplate % slider.GetValue())
        )
        slider.filterName = filterName
        slider.argName = labelTxt
        slider.script = script
        slider.argIndex = argIndex

        # Slider event binding
        def UserSliderVideoUpdateNew(slider):
            # Create the new arg text
            newVal = slider.GetValueAsString()
            self.SetNewAvsValue(slider, newVal)

        #~ slider.Bind(wx.EVT_LEFT_UP, self.OnLeftUpUserSlider)
        def OnLeftUpUserSlider(event):
            UserSliderVideoUpdateNew(slider)
            event.Skip()
        slider.Bind(wx.EVT_LEFT_UP, OnLeftUpUserSlider)

        # Create the static text labels
        labelTxtCtrl = self.MakeArgNameStaticText(parent, labelTxt, filterName, script, argIndex)
        minTxtCtrl = wx.StaticText(parent, wx.ID_ANY, strTemplate % minValue)
        maxTxtCtrl = wx.StaticText(parent, wx.ID_ANY, strTemplate % maxValue)
        valTxtCtrl = wx.StaticText(parent, wx.ID_ANY, strTemplate % value)
        valTxtCtrl.SetForegroundColour(wx.BLUE)
        valTxtCtrl.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
        value_formatted = strTemplate % defaultValue
        valTxtCtrl.SetToolTip(wx.ToolTip(_('Reset to default value: %(value_formatted)s') % locals()))
        def OnTextLeftDown(event):
            valTxtCtrl.SetLabel(value_formatted)
            slider.SetValue(defaultValue)
            UserSliderVideoUpdateNew(slider)
        valTxtCtrl.Bind(wx.EVT_LEFT_DOWN, OnTextLeftDown)
        leftCtrl = wxButtons.GenBitmapButton(parent, wx.ID_ANY, self.bmpLeftTriangle, size=(16,16))
        leftCtrl.SetBezelWidth(1)
        leftCtrl.SetUseFocusIndicator(False)
        def OnLeftTimer(event):
            newvalue = slider.Decrement()
            valTxtCtrl.SetLabel(strTemplate % newvalue)
            if leftCtrl.up:
                leftTimer.Stop()
                UserSliderVideoUpdateNew(slider)
                if leftCtrl.HasCapture():
                    leftCtrl.ReleaseMouse()
            event.Skip()
        leftTimer = wx.Timer(leftCtrl)
        leftCtrl.Bind(wx.EVT_TIMER, OnLeftTimer)
        def OnButtonDecLeftDown(event):
            newvalue = slider.Decrement()
            valTxtCtrl.SetLabel(strTemplate % newvalue)
            self.fc = wx.FutureCall(300, leftTimer.Start, 100)
            event.Skip()
        def OnButtonDecLeftUp(event):
            if self.fc is not None:
                self.fc.Stop()
            leftTimer.Stop()
            UserSliderVideoUpdateNew(slider)
            event.Skip()
        leftCtrl.Bind(wx.EVT_LEFT_DOWN, OnButtonDecLeftDown)
        leftCtrl.Bind(wx.EVT_LEFT_UP, OnButtonDecLeftUp)
        rightCtrl = wxButtons.GenBitmapButton(parent, wx.ID_ANY, self.bmpRightTriangle, size=(16,16))
        rightCtrl.SetBezelWidth(1)
        rightCtrl.SetUseFocusIndicator(False)
        def OnRightTimer(event):
            newvalue = slider.Increment()
            valTxtCtrl.SetLabel(strTemplate % newvalue)
            if rightCtrl.up:
                rightTimer.Stop()
                UserSliderVideoUpdateNew(slider)
                if rightCtrl.HasCapture():
                    rightCtrl.ReleaseMouse()
            event.Skip()
        rightTimer = wx.Timer(rightCtrl)
        rightCtrl.Bind(wx.EVT_TIMER, OnRightTimer)
        def OnButtonIncLeftDown(event):
            newvalue = slider.Increment()
            valTxtCtrl.SetLabel(strTemplate % newvalue)
            self.fc = wx.FutureCall(300, rightTimer.Start, 100)
            event.Skip()
        def OnButtonIncLeftUp(event):
            if self.fc is not None:
                self.fc.Stop()
            rightTimer.Stop()
            UserSliderVideoUpdateNew(slider)
            event.Skip()
        rightCtrl.Bind(wx.EVT_LEFT_DOWN, OnButtonIncLeftDown)
        rightCtrl.Bind(wx.EVT_LEFT_UP, OnButtonIncLeftUp)
        # Add the elements to the sliderSizer
        sizer.Add(labelTxtCtrl, (row,0), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.LEFT, 10)
        sizer.Add(minTxtCtrl, (row,1), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        sizer.Add(leftCtrl, (row,2), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL|wx.LEFT, 5)
        sizer.Add(slider, (row,3), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)
        sizer.Add(rightCtrl, (row,4), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        sizer.Add(maxTxtCtrl, (row,5), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        sizer.Add(valTxtCtrl, (row,6), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 0)
        #sizer.Add((10, -1), (row,7))
        separator.controls += [labelTxtCtrl, minTxtCtrl, leftCtrl, slider, rightCtrl, maxTxtCtrl, valTxtCtrl]
        separator.hasNumericalSlider = True

    def ValidateAvsSliderInputs(self, strDef, strMin, strMax, strMod):
        # Returns (error type, error message)
        # Error types: None: good / 0: bad default / 1: bad min / 2: bad max / 3: bad mod / -1: non-number
        errortype = errormessage = None
        if strDef.startswith('$'):
            try:
                hexstring = strDef.split('$', 1)[1]
                int(hexstring, 16)
                return (None, None, [hexstring])
            except ValueError:
                return (0, _('Invalid hexadecimal color!'), None)
        if strMin and not strMax:
            return (2, _('Must specify a max value!'), None)
        if strMax and not strMin:
            return (1, _('Must specify a min value!'), None)
        try:
            minValue = float(strMin)
        except ValueError:
            #~ return (1, _('Min value must be a number!'), None)
            errortype = 1
            errormessage = _('Min value must be a number!')
        try:
            maxValue = float(strMax)
        except ValueError:
            #~ return (2, _('Max value must be a number!'), None)
            errortype = 2
            errormessage = _('Max value must be a number!')
        if not strDef:
            defValue = minValue
        else:
            try:
                defValue = float(strDef)
            except ValueError:
                #~ return (0, _('Default value must be a number!'), None)
                errortype = 0
                errormessage = _('Default value must be a number!')
        if not strMod:
            modValue = None
        else:
            try:
                modValue = int(float(strMod))
            except ValueError:
                #~ return (3, _('Step size must be an number!'), None)
                errortype = 3
                errormessage = _('Step size value must be a number!')
        if errormessage is not None:
            return (-1, errormessage, (strDef, strMin, strMax, strMod))
        if minValue >= maxValue:
            return (1, _('The min value must be less than the max!'), None)
        if defValue < minValue or defValue > maxValue:
            return (0,  _('The initial value must be between the min and the max!'), None)
        if modValue is not None and modValue >= 1:
            mod = modValue
            if int(minValue) % mod != 0:
                return (1, _('The min value must be a multiple of %(mod)s!') % locals(), None)
            if int(maxValue) % mod != 0:
                return (2, _('The max value must be a multiple of %(mod)s!') % locals(), None)
            if int(defValue) % mod != 0:
                return (0, _('The initial value must be a multiple of %(mod)s!') % locals(), None)
            if mod > (maxValue - minValue):
                return (0, _('The difference between the min and max must be greater than %(mod)s!') % locals(), None)
        return (None, None, (defValue, minValue, maxValue, modValue))

    def addAvsBooleanRadio(self, script, argname, value, defaultValue, row, separator, filterName, argIndex):
        parent = script.sliderWindow
        sizer = script.sliderSizerNew
        # Create window elements
        #~ labelTxtCtrl = wx.StaticText(parent, wx.ID_ANY, argname)
        labelTxtCtrl = self.MakeArgNameStaticText(parent, argname, filterName, script, argIndex)
        radioButtonTrue = wx.RadioButton(parent, wx.ID_ANY, 'true', style=wx.RB_GROUP, size=(-1,20))
        radioButtonFalse = wx.RadioButton(parent, wx.ID_ANY, 'false', size=(-1,20))
        if value:
            radioButtonTrue.SetValue(True)
        else:
            radioButtonFalse.SetValue(True)
        def OnRadioButton(event):
            button = event.GetEventObject()
            if button == radioButtonTrue:
                newVal = 'true'
            else:
                newVal = 'false'
            self.SetNewAvsValue(button, newVal)
            event.Skip()
        for ctrl in (radioButtonTrue, radioButtonFalse):
            ctrl.filterName = filterName
            ctrl.argName = argname
            ctrl.script = script
            ctrl.argIndex = argIndex
            ctrl.Bind(wx.EVT_RADIOBUTTON, OnRadioButton)
        if defaultValue is not None:
            if defaultValue.lower() == 'true':
                font = radioButtonTrue.GetFont()
                font.SetUnderlined(True)
                radioButtonTrue.SetFont(font)
            else:
                font = radioButtonFalse.GetFont()
                font.SetUnderlined(True)
                radioButtonFalse.SetFont(font)
        radioSizer = wx.BoxSizer(wx.HORIZONTAL)
        #~ radioSizer.Add((20,-1))
        radioSizer.Add(radioButtonTrue, 0, wx.TOP|wx.BOTTOM|wx.RIGHT, 5)
        radioSizer.Add(radioButtonFalse, 0, wx.ALL, 5)
        # Add the elements to the slider sizer
        sizer.Add(labelTxtCtrl, (row,0), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.LEFT, 10)
        #~ sizer.Add(radioButtonTrue, (row,1), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        #~ sizer.Add(radioButtonFalse, (row,2), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        sizer.Add(radioSizer, (row, 1), (1,6), wx.ALIGN_CENTER_VERTICAL)
        #sizer.Add((10, -1), (row,7))
        separator.controls += [labelTxtCtrl, radioSizer]
        #~ separator.controls += [labelTxtCtrl]

    def addAvsColorPicker(self, script, argname, value, defaultValue, row, separator, filterName, argIndex):
        parent = script.sliderWindow
        sizer = script.sliderSizerNew
        # Create window elements
        #~ labelTxtCtrl = wx.StaticText(parent, wx.ID_ANY, argname)
        labelTxtCtrl = self.MakeArgNameStaticText(parent, argname, filterName, script, argIndex)
        try:
            r = int(defaultValue[0:2],16)
            g = int(defaultValue[2:4],16)
            b = int(defaultValue[4:6],16)
            defaultColor = wx.Colour(r, g, b)
        except:
            defaultColor = wx.Colour()
        try:
            r = int(value[0:2],16)
            g = int(value[2:4],16)
            b = int(value[4:6],16)
        except:
            r=g=b=0
        colorButton = colourselect.ColourSelect(parent, wx.ID_ANY, colour=wx.Colour(r,g,b), size=(50,23))
        def OnSelectColour(event):
            strColor = '$%02x%02x%02x' % colorButton.GetColour().Get()
            self.SetNewAvsValue(colorButton, strColor.upper())
        colorButton.Bind(colourselect.EVT_COLOURSELECT, OnSelectColour)
        def OnRightUpButtonColor(event):
            colorButton.SetColour(defaultColor)
            self.SetNewAvsValue(colorButton, '$%s' % defaultValue.upper())
        colorButton.Bind(wx.EVT_RIGHT_UP, OnRightUpButtonColor)
        colorButton.SetToolTip(wx.ToolTip(_('Left-click to select a color, right click to reset to default')+' ($%s)' % defaultValue))

        colorButton.filterName = filterName
        colorButton.argName = argname
        colorButton.script = script
        colorButton.argIndex = argIndex

        #TODO: FIX
        colorSizer = wx.BoxSizer(wx.HORIZONTAL)
        colorSizer.Add(colorButton, 0, wx.TOP|wx.BOTTOM|wx.RIGHT, 5)
        # Add the elements to the slider sizer
        sizer.Add(labelTxtCtrl, (row,0), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.LEFT, 10)
        #~ sizer.Add(radioButtonTrue, (row,1), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        #~ sizer.Add(radioButtonFalse, (row,2), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        sizer.Add(colorSizer, (row, 1), (1,6), wx.ALIGN_CENTER_VERTICAL)
        #sizer.Add((10, -1), (row,7))
        separator.controls += [labelTxtCtrl, colorSizer]
        #~ separator.controls += [labelTxtCtrl]

    def addAvsStringChoice(self, script, argname, value, choices, defaultValue, row, separator, filterName, argIndex):
        parent = script.sliderWindow
        sizer = script.sliderSizerNew
        # Create window elements
        choices2 = choices[:]
        try:
            #~ index = choices.index(defaultValue)
            index = [s.strip('"').lower() for s in choices].index(defaultValue.strip('"').lower())
            choices2[index] = choices[index] + ' *'
        except ValueError:
            pass
        #~ labelTxtCtrl = wx.StaticText(parent, wx.ID_ANY, argname)
        labelTxtCtrl = self.MakeArgNameStaticText(parent, argname, filterName, script, argIndex)
        choiceBox = wx.Choice(parent, wx.ID_ANY, choices=choices2)
        try:
            index = [s.strip('"').lower() for s in choices].index(value.strip('"').lower())
            choiceBox.SetSelection(index)
        except ValueError:
            pass
        def OnChoice(event):
            newVal = '"%s"' % choices[choiceBox.GetCurrentSelection()].strip('"')
            self.SetNewAvsValue(choiceBox, newVal)
            event.Skip()
        choiceBox.filterName = filterName
        choiceBox.argName = argname
        choiceBox.script = script
        choiceBox.argIndex = argIndex
        choiceBox.Bind(wx.EVT_CHOICE, OnChoice)
        # Add the elements to the slider sizer
        sizer.Add(labelTxtCtrl, (row,0), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.LEFT, 10)
        #~ sizer.Add(radioButtonTrue, (row,1), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        #~ sizer.Add(radioButtonFalse, (row,2), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        sizer.Add(choiceBox, (row, 1), (1,6), wx.ALIGN_CENTER_VERTICAL)
        #sizer.Add((10, -1), (row,7))
        separator.controls += [labelTxtCtrl, choiceBox]

    def addAvsFilenamePicker(self, script, argname, value, extList, row, separator, filterName, argIndex):
        parent = script.sliderWindow
        sizer = script.sliderSizerNew
        # Create window elements
        #~ labelTxtCtrl = wx.StaticText(parent, wx.ID_ANY, argname)
        extList = [s.strip() for s in extList if not s.strip().startswith('*.*')]
        labelTxtCtrl = self.MakeArgNameStaticText(parent, argname, filterName, script, argIndex)
        textCtrl = wx.TextCtrl(parent, wx.ID_ANY, value)
        browseButton = wx.Button(parent, wx.ID_ANY, '...', size=(20, -1))
        def OnTextChange(event):
            script.oldAutoSliderInfo = None
            event.Skip()
        def OnTextEnter(event):
            newVal = '"%s"' % textCtrl.GetValue().strip(' "')
            self.SetNewAvsValue(textCtrl, newVal)
            event.Skip()
        def OnBrowseButton(event):
            dirname = os.path.dirname(textCtrl.GetValue())
            if os.path.isdir(dirname):
                recentdir = dirname
            else:
                recentdir = self.options['recentdir']
            extlist = self.options['templates'].keys()
            extlist.sort()
            extlist2 = [s for s in extlist if not s.startswith('avs')]
            extlist1 = ', '.join(extlist2)
            extlist2 = ';*.'.join(extlist2)
            s1 = '%s|%s' % (', '.join(extList), ';'.join(extList))
            s2 = _('Source files (%(extlist1)s)|*.%(extlist2)s') % locals() #'%s|%s' % (', '.join(extList), ';'.join(extList))
            s3 = _('All files (*.*)|*.*')
            if extList:
                filefilter = '%s|%s|%s' % (s1, s2, s3) #_('AviSynth script (avs, avsi)|*.avs;*.avsi|Source files (%(extlist1)s)|*.%(extlist2)s|All files (*.*)|*.*') %  locals()
            else:
                filefilter = s3
            dlg = wx.FileDialog(self,_('Select a file'), recentdir, '', filefilter, wx.OPEN)
            ID = dlg.ShowModal()
            if ID == wx.ID_OK:
                filename = dlg.GetPath()
                newVal = '"%s"' % filename
                self.SetNewAvsValue(browseButton, newVal)
                textCtrl.SetValue(filename)
                dirname = os.path.dirname(filename)
                if os.path.isdir(dirname):
                    self.options['recentdir'] = dirname
            dlg.Destroy()
            event.Skip()
        for ctrl in (textCtrl, browseButton):
            ctrl.filterName = filterName
            ctrl.argName = argname
            ctrl.script = script
            ctrl.argIndex = argIndex
        self.Bind(wx.EVT_BUTTON, OnBrowseButton, browseButton)
        textCtrl.Bind(wx.EVT_TEXT_ENTER, OnTextEnter)
        textCtrl.Bind(wx.EVT_TEXT, OnTextChange)
        browseSizer = wx.BoxSizer(wx.HORIZONTAL)
        #~ radioSizer.Add((20,-1))
        browseSizer.Add(textCtrl, 1, wx.EXPAND|wx.RIGHT, 2)#|wx.TOP|wx.BOTTOM|wx.RIGHT, 5)
        browseSizer.Add(browseButton, 0)#, wx.ALL, 5)
        # Add the elements to the slider sizer
        sizer.Add(labelTxtCtrl, (row,0), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.LEFT, 10)
        #~ sizer.Add(radioButtonTrue, (row,1), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        #~ sizer.Add(radioButtonFalse, (row,2), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 10)
        #~ sizer.Add(textCtrl, (row, 3), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)
        #~ sizer.Add(browseButton, (row, 4), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(browseSizer, (row,1), (1,6), wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)
        #sizer.Add((10, -1), (row,7))
        #~ separator.controls += [labelTxtCtrl, textCtrl, browseButton]
        separator.controls += [labelTxtCtrl, browseSizer]
        #~ separator.controls += [labelTxtCtrl]

    def addAvsGenericArg(self, script, argname, strValue, row, separator, filterName, argIndex):
        parent = script.sliderWindow
        sizer = script.sliderSizerNew
        # Create window elements
        labelTxtCtrl = self.MakeArgNameStaticText(parent, argname, filterName, script, argIndex)

        textCtrl = wx.TextCtrl(parent, wx.ID_ANY, strValue, style=wx.TE_PROCESS_ENTER)
        def OnTextChange(event):
            self.SetNewAvsValue(textCtrl, textCtrl.GetValue(), refreshvideo=False)
            #~ script.oldAutoSliderInfo = None
            event.Skip()
        def OnTextEnter(event):
            self.SetNewAvsValue(textCtrl, textCtrl.GetValue())
            #~ event.Skip()
        textCtrl.Bind(wx.EVT_TEXT, OnTextChange)
        textCtrl.Bind(wx.EVT_TEXT_ENTER, OnTextEnter)
        textCtrl.filterName = filterName
        textCtrl.argName = argname
        textCtrl.script = script
        textCtrl.argIndex = argIndex

        #~ tempSizer = wx.BoxSizer()
        #~ tempSizer.Add(labelTxtCtrl, 0, wx.TOP|wx.BOTTOM, 4)
        #~ sizer.Add(tempSizer, (row,0), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.LEFT, 10)
        #~ sizer.Add((10, -1), (row,7))
        #~ separator.controls += [tempSizer]
        sizer.Add(labelTxtCtrl, (row,0), wx.DefaultSpan, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.LEFT, 10)
        sizer.Add(textCtrl, (row,1), (1,6), wx.ALIGN_CENTER_VERTICAL|wx.EXPAND)
        #sizer.Add((10, -1), (row,7))
        separator.controls += [labelTxtCtrl, textCtrl]

    def MakeArgNameStaticText(self, parent, labelTxt, filterName, script, argIndex, size=wx.DefaultSize):
        labelTxtCtrl = wx.StaticText(parent, wx.ID_ANY, labelTxt, size=size)
        labelTxtCtrl.SetCursor(wx.StockCursor(wx.CURSOR_PENCIL))
        labelTxtCtrl.filterName = filterName
        labelTxtCtrl.argName = labelTxt
        labelTxtCtrl.script = script
        labelTxtCtrl.argIndex = argIndex
        def OnLeftDown(event):
            selText, selA, selB = self.GetArgTextAndPos(labelTxtCtrl)
            if selText.startswith('"') and selText.endswith('"'):
                selA += 1
                selB -= 1
            script.SetSelection(selA, selB)
            script.EnsureCaretVisible()
            script.SetFocus()
            event.Skip()
        labelTxtCtrl.Bind(wx.EVT_LEFT_DOWN, OnLeftDown)
        return labelTxtCtrl

    def SetNewAvsValue(self, control, newValue, refreshvideo=True):
        script = control.script
        argText, posA, posB = self.GetArgTextAndPos(control)
        if argText is None:
            return
        # Create the new arg text
        script.SetTargetStart(posA)
        script.SetTargetEnd(posB)
        script.ReplaceTarget(newValue)
        if refreshvideo:
            self.refreshAVI = True
            self.ShowVideoFrame(userScrolling=True)

    def GetArgTextAndPos(self, slider):
        # Find the filter in the text
        script = slider.script
        splitFilterName = slider.filterName.split('(', 1)
        if len(splitFilterName) == 2:
            filterName = splitFilterName[0].strip()
            iFilter = splitFilterName[1].split(')')[0]
            try:
                iFilter = int(iFilter)
            except ValueError:
                return (None, None, None)
        else:
            filterName = slider.filterName
            iFilter = 1
        startpos = 0
        for i in range(iFilter):
            startpos = script.FindText(startpos, script.GetTextLength(), filterName, stc.STC_FIND_WHOLEWORD)
            if startpos == -1:
                return (None, None, None)
            startpos += 1
            while script.GetStyleAt(startpos) not in script.keywordStyleList:
                startpos = script.FindText(startpos, script.GetTextLength(), filterName, stc.STC_FIND_WHOLEWORD)
                if startpos == -1:
                    return (None, None, None)
                startpos += 1
        # Find the argument in the text
        endwordpos = script.WordEndPosition(startpos, 1)
        posEnd = script.BraceMatch(endwordpos)
        if posEnd == -1:
            return (None, None, None)
        argIndex = slider.argIndex
        for i in xrange(argIndex):
            endwordpos = script.GetNextValidCommaPos(endwordpos+1)
            if endwordpos is None:
                return (None, None, None)
        posA = endwordpos+1
        posB = script.GetNextValidCommaPos(posA)
        if posB is None or posB > posEnd:
            posB = posEnd
        text = script.GetTextRange(posA, posB)
        posEqualSign = script.GetNextValidCommaPos(posA, checkChar='=')
        if posEqualSign is not None and posEqualSign < posB:
            posA = posEqualSign+1
        pos = posA
        while pos < posB:
            c = unichr(script.GetCharAt(pos))
            if c.strip() and c != '\\':
                posA = pos
                break
            pos += 1
        pos = posB
        while pos > posA:
            c = unichr(script.GetCharAt(pos-1))
            if c.strip() and c != '\\':
                posB = pos
                break
            pos -= 1
        return script.GetTextRange(posA, posB), posA, posB

    def addAvsSliderSeparatorNew(self, script, label='', menu=None, row=None, sizer=None):
        if sizer is None:
            sizer = script.sliderSizer
        parent = script.sliderWindow
        color1 = wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DSHADOW)
        color2 = wx.SystemSettings.GetColour(wx.SYS_COLOUR_3DHILIGHT)
        # Add a separator
        tempsizer = wx.BoxSizer(wx.VERTICAL)
        if row == 0: border = 0 if wx.VERSION < (2, 9) else 5
        else: border = 10
        if label == '':
            tempsizer.Add(wx.StaticLine(parent), 0, wx.EXPAND|wx.ALIGN_BOTTOM|wx.TOP, border)
        else:
            staticText = wx.StaticText(parent, wx.ID_ANY, ' - '+label)
            staticText.SetCursor(wx.StockCursor(wx.CURSOR_HAND))
            def OnLeftDown(event):
                separator = event.GetEventObject()
                self.ToggleSliderFold(separator, separator.IsControlsVisible)
                event.Skip()
            staticText.Bind(wx.EVT_LEFT_DOWN, OnLeftDown)

            if menu is not None:
                staticText.contextMenu = menu
                staticText.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)

            font = staticText.GetFont()
            font.SetWeight(wx.FONTWEIGHT_BOLD)
            staticText.SetFont(font)
            tempsizer.Add(staticText, 0, wx.ALIGN_BOTTOM|wx.TOP, border)
            tempsizer.Add(wx.StaticLine(parent), 0, wx.EXPAND|wx.ALIGN_BOTTOM)
        sizer.Add(tempsizer, (row,0), (1,7), wx.EXPAND)
        staticText.controls = []
        staticText.hasNumericalSlider = False
        staticText.IsControlsVisible = True
        script.sliderToggleLabels.append(staticText)
        return staticText

    def ToggleSliderFold(self, separator, fold=True, refresh=True):
        sizer = self.currentScript.sliderSizerNew
        parent = separator.GetParent()
        parent.Freeze()
        if fold:
            for item in separator.controls:
                sizer.Hide(item)
            separator.SetLabel('+ '+separator.GetLabel().strip(' -+'))
            separator.IsControlsVisible = False
        else:
            for item in separator.controls:
                sizer.Show(item)
            separator.SetLabel(' - '+separator.GetLabel().strip(' -+'))
            separator.IsControlsVisible = True
        if refresh:
            sizer.Layout()
            parent.FitInside()
            parent.Refresh()
            if separator.IsControlsVisible and separator.controls:
                lastitem = separator.controls[-1]
                if lastitem.GetPosition()[1]+lastitem.GetSize()[1] > parent.GetSize()[1]:
                    xscrollpixels, yscrollpixels = parent.GetScrollPixelsPerUnit()
                    pos = parent.CalcUnscrolledPosition(separator.GetPosition())
                    parent.Scroll(-1, (pos[1]-10)/yscrollpixels)
        parent.Thaw()

    def createToggleTagCheckboxes(self, script):
        toggleTags = script.toggleTags
        # First remove all old checkboxes
        script.toggleTagSizer.Clear(deleteWindows=True)
        labels = []
        # Then add the new checkboxes
        for tag in toggleTags:
            label, boolCheck = tag
            if label not in labels:
                checkbox = wx.CheckBox(script.sliderWindow, wx.ID_ANY, _('Toggle "%(label)s" section') % locals(), name=label)
                checkbox.SetValue(boolCheck)
                checkbox.Bind(wx.EVT_CHECKBOX, self.OnToggleTagChecked)
                script.toggleTagSizer.Add(checkbox, 0, wx.BOTTOM, 15)
                labels.append(label)

    def SetScriptTabname(self, script):
        if script == self.scriptNotebook.GetCurrentPage():
            index = self.scriptNotebook.GetSelection()
        else:
            for index in xrange(self.scriptNotebook.GetPageCount()):
                if script == self.scriptNotebook.GetPage(index):
                    break
        title = self.scriptNotebook.GetPageText(index).lstrip('* ')
        if script.GetModify():
            title = '* '+title
        self.scriptNotebook.SetPageText(index, title)
        self.SetProgramTitle()

    def SetProgramTitle(self):
        tabname = self.getScriptTabname()
        self.SetTitle('%s - %s' % (tabname, self.name))
        if self.separatevideowindow:
            #~ self.videoDialog.SetTitle(_('AvsP') + ' - ' + self.getScriptTabname(allowfull=True))
            self.videoDialog.SetTitle('%s - [%s]' % (tabname, self.name))

    def getScriptTabname(self, allowfull=True):
        index = self.scriptNotebook.GetSelection()
        tabname = self.scriptNotebook.GetPageText(index)
        filename = self.currentScript.filename
        #~ if allowfull and self.options['showfullname'] and filename:
        if allowfull and filename:
            if self.currentScript.GetModify():
                tabname = '* ' + filename
            else:
                tabname = filename
        return tabname

    def UpdateTabImages(self):
        if self.options['usetabimages']:
            if self.options['multilinetab']:
                rows = self.scriptNotebook.GetRowCount()
            if self.FindFocus() == self.videoWindow:
                for i in xrange(min(self.scriptNotebook.GetPageCount(), 10)):
                    self.scriptNotebook.SetPageImage(i, i)
            else:
                #~ il = self.scriptNotebook.GetImageList()
                for i in xrange(self.scriptNotebook.GetPageCount()):
                    self.scriptNotebook.SetPageImage(i, -1)
            if self.options['multilinetab']:
                if rows != self.scriptNotebook.GetRowCount():
                    w, h = self.scriptNotebook.GetSize()
                    self.scriptNotebook.SetSize((w, h-1))
                    self.scriptNotebook.SetSize((w, h))

    def ShowWarningOnBadNaming(self, dllnameList):
        wx.Bell()
        dlg = wx.Dialog(self, wx.ID_ANY, _('Warning'))
        bmp = wx.StaticBitmap(dlg, wx.ID_ANY, wx.ArtProvider.GetBitmap(wx.ART_WARNING))
        dllnameList.append('\n')
        message = wx.StaticText(dlg, wx.ID_ANY, '.dll\n'.join(dllnameList) +\
                                                _('Above plugin names contain undesirable symbols.\n'
                                                  'Rename them to only use alphanumeric or underscores,\n'
                                                  'or make sure to use them in short name style only.'))
        msgsizer = wx.BoxSizer(wx.HORIZONTAL)
        msgsizer.Add(bmp)
        msgsizer.Add(message, 0, wx.LEFT, 10)
        
        checkbox = wx.CheckBox(dlg, wx.ID_ANY, _("Don't show me this again"))
        btnsizer = dlg.CreateStdDialogButtonSizer(wx.OK)
        
        dlgsizer = wx.BoxSizer(wx.VERTICAL)
        dlgsizer.Add(msgsizer, 0, wx.ALL, 10)
        dlgsizer.Add(checkbox, 0, wx.LEFT, 10)
        dlgsizer.Add(btnsizer, 0, wx.ALL|wx.ALIGN_CENTER, 10)
        dlg.SetSizerAndFit(dlgsizer)
        dlg.ShowModal()
        self.options['dllnamewarning'] = not checkbox.IsChecked()
        dlg.Destroy()
    
    def getMacrosLabelFromFile(self, filename):
        f = open(filename)
        text = f.readline().strip('#').strip()
        f.close()
        return text
        
    # Macro-related functions
    def MacroIsMenuChecked(self, text):
        if text.count('->') > 0:
            # text is the menu command name
            index = 0
        else:
            # text is the menu command shortcut string
            index = 1
        # Search through self.optionsShortcuts for a match
        if text == '':
            return False
        if self.macrosStack:
            menuItem = self.GetMenuBar().GetMenu(self.macroMenuPos).FindItemById(self.macrosStack[-1])
            menu = menuItem.GetMenu()
        else:
            menu = None
        for item in self.options['shortcuts']:
            if text.lower() == item[index].lower():
                id = item[2]
                menuItem = self.GetMenuBar().FindItemById(id)
                if menuItem.IsCheckable():
                    return menuItem.IsChecked()
                return False
            # assume using a incomplete text, search under the menu of the current running macro
            elif menu and item[0].lower().endswith(text.lower()):
                id = item[2]
                menuItem = menu.FindItemById(id)
                if menuItem:
                    if menuItem.IsCheckable():
                        return menuItem.IsChecked()
                    return False
        return False
            
    def MacroExecuteMenuCommand(self, text, callafter=False):
        if text.count('->') > 0:
            # text is the menu command name
            index = 0
        else:
            # text is the menu command shortcut string
            index = 1
        # Search through self.optionsShortcuts for a match
        if text == '':
            return False
        if self.macrosStack:
            menuItem = self.GetMenuBar().GetMenu(self.macroMenuPos).FindItemById(self.macrosStack[-1])
            menu = menuItem.GetMenu()
        else:
            menu = None
        for item in self.options['shortcuts']:
            if text.lower() == item[index].lower():
                id = item[2]
                event = wx.CommandEvent(wx.wxEVT_COMMAND_MENU_SELECTED, id)
                if callafter:
                    self.GetEventHandler().AddPendingEvent(event)
                else:
                    self.GetEventHandler().ProcessEvent(event)
                return True
            # assume using a incomplete text, search under the menu of the current running macro
            elif menu and item[0].lower().endswith(text.lower()):
                id = item[2]
                menuItem = menu.FindItemById(id)
                if menuItem:
                    event = wx.CommandEvent(wx.wxEVT_COMMAND_MENU_SELECTED, id)
                    if callafter:
                        self.GetEventHandler().AddPendingEvent(event)
                    else:
                        self.GetEventHandler().ProcessEvent(event)
                    return True
        return False

    def MacroSaveScript(self, filename='', index=None):
        script, index = self.getScriptAtIndex(index)
        if script is None:
            return ''
        if filename == '':
            filename = script.filename
        self.SaveScript(script.filename, index)
        return script.filename

    def MacroIsScriptSaved(self, index=None):
        script, index = self.getScriptAtIndex(index)
        if script is None:
            return False
        return (not script.GetModify())

    def MacroGetScriptFilename(self, index=None):
        script, index = self.getScriptAtIndex(index)
        if script is None:
            return None
        return script.filename

    def MacroShowVideoFrame(self, framenum=None, index=None, forceRefresh=False):
        # Get the desired script
        script, index = self.getScriptAtIndex(index)
        if script is None:
            return False
        self.ShowVideoFrame(framenum, forceRefresh=forceRefresh, script=script)
        self.SelectTab(index)
        self.Refresh()
        self.Update()
        return True

    def MacroShowVideoOffset(self, offset=0, units='frames', index=None):
        # Get the desired script
        script, index = self.getScriptAtIndex(index)
        if script is None:
            return False
        self.ShowVideoOffset(offset=offset, units=units)
        self.SelectTab(index)
        #~ self.Refresh()
        self.Update()

    def MacroUpdateVideo(self, index=None):
        script, index = self.getScriptAtIndex(index)
        if script is None:
            return False
        if self.previewWindowVisible:
            self.ShowVideoFrame(forceRefresh=True, script=script)
        else:
            self.UpdateScriptAVI(script, forceRefresh=True)
        if script.AVI is None or script.AVI.IsErrorClip():
            return False
        return True

    def MacroWriteToScrap(self, txt, pos=-1):
        if not self.scrapWindow.IsShown():
            win = self.FindFocus()
            self.scrapWindow.Show()
            win.SetFocus()
        if self.InsertText(txt, pos, index=-1):
            scrap = self.scrapWindow.textCtrl
            txtLength = len(txt)
            txtPos = scrap.GetCurrentPos() - txtLength
            scrap.StartStyling(txtPos, 31)
            scrap.SetStyling(txtLength, stc.STC_P_WORD)
            scrap.nInserted += 1
            scrap.Refresh()
            scrap.Update()
            def UndoStyling(scrap):
                #~ totalLength = scrap.GetTextLength()
                #~ if txtPos > totalLength:
                    #~ return
                #~ scrap.StartStyling(txtPos, 31)
                #~ scrap.SetStyling(min(txtLength, totalLength - txtPos), stc.STC_STYLE_DEFAULT)
                if scrap.nInserted > 0:
                    scrap.nInserted -= 1
                if scrap.nInserted == 0:
                    scrap.StartStyling(0, 31)
                    scrap.SetStyling(scrap.GetTextLength(), stc.STC_STYLE_DEFAULT)
            wx.FutureCall(1000, UndoStyling, scrap)
            return True
        else:
            return False

    def MacroGetScrapText(self):
        return self.scrapWindow.GetText()

    def MacroReplaceText(self, old, new):
        script = self.currentScript
        txt = script.GetText().replace(old, new)
        script.SetText(txt)
        script.GotoPos(script.GetLength())

    def MacroSetText(self, txt, index=None):
        # Get the desired script
        script, index = self.getScriptAtIndex(index)
        if script is None:
            return False
        # Replace the script's text
        script.SetText(str(txt))
        return True

    def MacroGetText(self, index=None):
        script, index = self.getScriptAtIndex(index)
        if script is None:
            return False
        return script.GetText()

    def MacroGetSelectedText(self, index=None):
        script, index = self.getScriptAtIndex(index)
        if script is None:
            return False
        return script.GetSelectedText()

    def MacroGetFilename(self, title=_('Open a script or source'), filefilter=None):
        if filefilter is None:
            extlist = self.options['templates'].keys()
            extlist.sort()
            extlist1 = ', '.join(extlist)
            extlist2 = ';*.'.join(extlist)
            filefilter = _('Source files (%(extlist1)s)|*.%(extlist2)s|All files (*.*)|*.*') %  locals()
        dlg = wx.FileDialog(self, title,
            self.options['recentdir'], '', filefilter, wx.OPEN|wx.FILE_MUST_EXIST)
        ID = dlg.ShowModal()
        if ID == wx.ID_OK:
            filename = dlg.GetPath()
            dirname = os.path.dirname(filename)
            if os.path.isdir(dirname):
                self.options['recentdir'] = dirname
        else:
            filename = ''
        dlg.Destroy()
        return filename

    def MacroGetSaveFilename(self, title=_('Save as'), filefilter = _('All files (*.*)|*.*')):
        dlg = wx.FileDialog(self, title,
            self.options['recentdir'], '', filefilter, wx.SAVE|wx.OVERWRITE_PROMPT)
        ID = dlg.ShowModal()
        if ID == wx.ID_OK:
            filename = dlg.GetPath()
            dirname = os.path.dirname(filename)
            if os.path.isdir(dirname):
                self.options['recentdir'] = dirname
        else:
            filename = ''
        dlg.Destroy()
        return filename

    def MacroGetDirectory(self, title=_('Select a directory')):
        # Get the avisynth directory from the user with a dialog box
        dlg = wx.DirDialog(self, title, self.options['recentdir'])
        ID = dlg.ShowModal()
        if ID==wx.ID_OK:
            dirname = dlg.GetPath()
            if os.path.isdir(dirname):
                self.options['recentdir'] = dirname
        else:
            dirname = ''
        dlg.Destroy()
        return dirname

    def MacroGetTextEntry(self, message=[''], default=[''], title=_('Enter information'), types=[''], width=400):
        r'''GetTextEntry(message='', default='', title='Enter information', types='text', width=400)
        
        Multiple entry dialog box.  In its more simple form displays a dialog box with 
        the string 'message' along with a field for text entry, initially filled with 
        the string 'default', returning the string from the text entry field if the 
        user clicked "OK", an empty string otherwise.
        
        title: title of the dialog box.
        
        The 'message', 'default' and 'types' parameters are list of lists.  If a list 
        were to contain only one component then it's not mandatory to wrap it as list.
        
        message: list of the lines of the dialog box, in which every component is a 
        list of the corresponding text strings to the entries in that line.  There must 
        be as many strings as desired entries.
        
        default: list of lists holding tuples with the default values for each entry.  
        In the same way as lists, if a tuple were to contain only one element then 
        it's not necessary to wrap it.  Each tuple and the whole parameter are optional 
        except for list entry type.
        
        types: list of lists containing the types of each entry.  Each value and the 
        whole parameter are optional.  Every omitted entry type defaults to a regular 
        text field.
        
        Types available:
        
        - 'text': regular text field.
          'default' values: 1-tuple with the initial field text.
        
        - 'file_open': text field with additional browse for file button ("open" 
              dialog).
          'default' values: 1-tuple or 2-tuple, with the initial field text and an 
              optional file wildcard with this syntax: 
              "BMP files (*.bmp)|*.bmp|GIF files (*.gif)|*.gif"
        
        - 'file_save': same as 'file_open', but with a "save" dialog.
        
        - 'dir': text field with additional browse for directory button.
          'default' values: 1-tuple with the initial field text.
        
        - 'list_read_only': drop-down list.  The 'default' tuple is mandatory.
          'default' values: n+1 tuple, where the first n elements are the strings 
              than compose the list and the last one is the entry selected by default.
        
        - 'list_writable': same as above but with the text field direcly writable, so 
              the return value is not limited to a selection from the list.
        
        - 'check': simple check box, returning True if checked.
          'default' values: 1-tuple with the predetermined boolean value, False as 
              default.
        
        - 'spin': numeric entry, with arrows to increment and decrement the value.
          'default' values: up-to-5-tuple, containing the default, minimum, maximum, 
              decimal digits shown and increment when using the arrows. With zero 
              decimal digits returns int, float otherwise. 
              Default: (0, None, None, 0, 1)
        
        - 'slider_h': horizontal slider. Similar to 'spin', but with a draggable handle.
          'default' values: up-to-4-tuple containing the default, minimum, maximum and 
              space between ticks marks that can be displayed alongside the slider. 
              Default: (50, 0, 100, no ticks)
        
        - 'slider_v': vertical slider, same as above.
        
        - 'sep': separator formed by a text string and a horizontal line.
          'default' values: 1-tuple with an optional fixed line length (by default 
              it extends through all the dialog's width).  Note that an invisible 
              separator can be created by setting 'message' to '' and 'default' to 
              0.  To include the 'default' parameter but don't give a fixed length 
              (e.g. there's more entries following that one) set the tuple to None 
              or any not-convertible-to-int value, like ''.
        
        A not recognized type string, including '', defaults to 'text' type.
        
        width: horizontal length of the dialog box.  The width is distributed uniformly 
        between the entries in each line.
        
        Return values: list of entered values if the user clicks "OK", empty list 
        otherwise.
        
        '''
        # Complete the 'default' and 'types' lists
        optionsDlgInfo = [['']]
        options = OrderedDict()
        cont = 0
        if not isinstance(message, MutableSequence): message = [message]
        if not isinstance(default, MutableSequence): default = [default] 
        if not isinstance(types, MutableSequence): types = [types] 
        default += [''] * (len(message) - len(default))
        types +=  [''] * (len(message) - len(types))
        for eachMessageLine, eachDefaultLine, eachTypeLine in zip(message, default, types):
            if not isinstance(eachMessageLine, MutableSequence): eachMessageLine = [eachMessageLine] 
            if not isinstance(eachDefaultLine, MutableSequence): eachDefaultLine = [eachDefaultLine] 
            if not isinstance(eachTypeLine, MutableSequence): eachTypeLine = [eachTypeLine] 
            lineLen=len(eachMessageLine)
            eachDefaultLine += [''] * (lineLen - len(eachDefaultLine))
            eachTypeLine +=  [''] * (lineLen - len(eachTypeLine))
            rowOptions = []
            for eachMessage, eachDefault, eachType in zip(eachMessageLine, eachDefaultLine, eachTypeLine):
                if not isinstance(eachDefault, Sequence) or isinstance(eachDefault, basestring):
                    eachDefault = (eachDefault,)

                #  Set 'optionsDlgInfo' and 'options' from the kind of more user friendly 'message', 'default' and 'types'
                
                if eachType in ('file_open', 'file_save'):
                    flag = (wxp.OPT_ELEM_FILE_OPEN if eachType == 'file_open' 
                            else wxp.OPT_ELEM_FILE_SAVE )
                    key = 'mgte' + str(cont)
                    cont += 1
                    misc = dict(width=width / lineLen, 
                        fileMask=eachDefault[1] if len(eachDefault) > 1 else '*.*', 
                        startDirectory=os.path.dirname(self.MacroGetScriptFilename()), 
                        buttonText='...', buttonWidth=30, label_position=wx.VERTICAL, 
                        expand=True)
                    colOptions = [eachMessage, flag, key, '', misc]
                    options[key] = eachDefault[0]
                
                elif eachType == 'dir':
                    flag = wxp.OPT_ELEM_DIR
                    key = 'mgte' + str(cont)
                    cont += 1
                    misc = dict(width=width / lineLen, 
                        startDirectory=os.path.dirname(self.MacroGetScriptFilename()), 
                        buttonText='...', buttonWidth=30, label_position=wx.VERTICAL, 
                        expand=True)
                    colOptions = [eachMessage, flag, key, '', misc]
                    options[key] = eachDefault[0]
                
                elif eachType in ('list_writable', 'list_read_only'):
                    flag = wxp.OPT_ELEM_LIST
                    key = 'mgte' + str(cont)
                    cont += 1
                    misc = dict(width=width / lineLen, choices=eachDefault[:-1], 
                        writable=True if eachType == 'list_writable' else False, 
                        label_position=wx.VERTICAL, expand=True)
                    colOptions = [eachMessage, flag, key, '', misc]
                    options[key] = eachDefault[-1]
                
                elif eachType == 'check':
                    flag = wxp.OPT_ELEM_CHECK
                    key = 'mgte' + str(cont)
                    cont += 1
                    misc = dict(width=width / lineLen)
                    colOptions = [eachMessage, flag, key, '', misc]
                    options[key] = eachDefault[0] if eachDefault[0] else False
                
                elif eachType == 'spin':
                    flag = wxp.OPT_ELEM_SPIN
                    key = 'mgte' + str(cont)
                    cont += 1
                    misc = dict(width=width / lineLen, label_position=wx.VERTICAL, 
                                expand=True)
                    params = ('min_val', 'max_val', 'digits', 'increment')
                    for i, param in enumerate(eachDefault[1:]):
                        if isinstance(param, basestring):
                            try:
                                misc[params[i]] = int(param)
                            except:
                                misc[params[i]] = float(param)
                        else:
                            misc[params[i]] = param
                    colOptions = [eachMessage, flag, key, '', misc]
                    options[key] = float(eachDefault[0]) if eachDefault[0] else 0
                
                elif eachType in ('slider_h', 'slider_v'):
                    flag = wxp.OPT_ELEM_SLIDER
                    key = 'mgte' + str(cont)
                    cont += 1
                    if eachType == 'slider_v':
                        orientation = wx.VERTICAL
                        width = 150
                    else:
                        orientation = wx.HORIZONTAL
                        width = width / lineLen
                    misc = dict(width=width, label_position=wx.VERTICAL, 
                                orientation=orientation, expand=True)
                    params = ('minValue', 'maxValue', 'TickFreq')
                    for i, param in enumerate(eachDefault[1:]):
                        misc[params[i]] = int(param)
                    colOptions = [eachMessage, flag, key, '', misc]
                    options[key] = int(eachDefault[0]) if eachDefault[0] != '' else 50
                
                elif eachType == 'sep':
                    flag = wxp.OPT_ELEM_SEP
                    try:
                        sep_width = int(eachDefault[0])
                    except:
                        misc = dict()
                    else:
                        misc = dict(width=sep_width, expand=False)
                    colOptions = [eachMessage, flag, 'mgte_sep', '', misc]
                
                else:
                    flag = ''
                    key = 'mgte' + str(cont)
                    cont += 1
                    misc = dict(width=width / lineLen, label_position=wx.VERTICAL)
                    colOptions = [eachMessage, flag, key, '', misc]
                    options[key] = str(eachDefault[0])
                
                rowOptions.append(colOptions)        
            optionsDlgInfo[0].append(rowOptions)
        
        # Open the dialog box and get the values
        dlg = wxp.OptionsDialog(self, optionsDlgInfo, options, title, starText=False)
        ID = dlg.ShowModal()
        values = []
        if ID == wx.ID_OK:
            values_dic = dlg.GetDict()
            for key in options.keys():
                values.append(values_dic[key])
        dlg.Destroy()
        if len(message) == 1:
            if values:
                return values[0]
            return ''
        return values
  
    def MacroMsgBox(self, message, title='', cancel=False):
        r'''MsgBox(message, title='', cancel=False)
        
        Displays a simple dialog box with the text string 'message' and title 'title', 
        and an additional cancel button if 'cancel' is True.  Returns True if the user 
        presses 'OK' and the cancel button is present, or always True if it's not.
        
        '''
        style = wx.OK
        if title == _('Error'):
            style |= wx.ICON_ERROR
        elif title == _('Warning'):
            style |= wx.ICON_EXCLAMATION
        if cancel:
            style |= wx.CANCEL
        action = wx.MessageBox(message, title, style)
        return True if action == wx.OK else False
    
    def MacroProgressBox(self, max=100, message='', title=_('Progress')):
        return wx.ProgressDialog(
            title, message, max,
            style=wx.PD_CAN_ABORT|wx.PD_ELAPSED_TIME|wx.PD_REMAINING_TIME
        )

    def MacroGetScriptCount(self):
        return self.scriptNotebook.GetPageCount()

    def MacroGetCurrentIndex(self):
        return self.scriptNotebook.GetSelection()

    def _x_MacroGetTabFilename(self, index=None):
        script, index = self.getScriptAtIndex(index)
        if script is None:
            return False
        return script.filename

    def MacroSaveImage(self, filename='', framenum=None, index=None):
        script, index = self.getScriptAtIndex(index)
        if script is None:
            return False
        self.refreshAVI = True
        
        
        
        self.MacroShowVideoFrame(framenum, index)
        if self.UpdateScriptAVI(script) is None:
            wx.MessageBox(_('Error loading the script'), _('Error'), style=wx.OK|wx.ICON_ERROR)
            return
        return self.SaveCurrentImage(filename, index)

    def MacroGetVideoWidth(self, index=None):
        script, index = self.getScriptAtIndex(index)
        if script is None:
            return False
        self.refreshAVI = True
        #~ self.MacroShowVideoFrame(None, index)
        if self.UpdateScriptAVI(script) is None:
            wx.MessageBox(_('Error loading the script'), _('Error'), style=wx.OK|wx.ICON_ERROR)
            return False
        return script.AVI.WidthActual

    def MacroGetVideoHeight(self, index=None):
        script, index = self.getScriptAtIndex(index)
        if script is None:
            return False
        self.refreshAVI = True
        #~ self.MacroShowVideoFrame(None, index)
        if self.UpdateScriptAVI(script) is None:
            wx.MessageBox(_('Error loading the script'), _('Error'), style=wx.OK|wx.ICON_ERROR)
            return False
        return script.AVI.HeightActual

    def MacroGetVideoFramerate(self, index=None):
        script, index = self.getScriptAtIndex(index)
        if script is None:
            return False
        self.refreshAVI = True
        #~ self.MacroShowVideoFrame(None, index)
        if self.UpdateScriptAVI(script) is None:
            wx.MessageBox(_('Error loading the script'), _('Error'), style=wx.OK|wx.ICON_ERROR)
            return False
        return script.AVI.Framerate

    def MacroGetVideoFramecount(self, index=None):
        script, index = self.getScriptAtIndex(index)
        if script is None:
            return False
        self.refreshAVI = True
        #~ self.MacroShowVideoFrame(None, index)
        if self.UpdateScriptAVI(script) is None:
            wx.MessageBox(_('Error loading the script'), _('Error'), style=wx.OK|wx.ICON_ERROR)
            return False
        return script.AVI.Framecount

    def MacroRunExternalPlayer(self, executable=None, args='', index=None):
        if executable is None:
            executable = self.options['externalplayer']
        script, index = self.getScriptAtIndex(index)
        if script is None:
            return False
        if not self.RunExternalPlayer(executable, script, args, prompt=False):
            return False
        return True

    def MacroGetBookmarkFrameList(self, title=False):
        bookmarkList = [value for value, bmtype in self.GetBookmarkFrameList() if bmtype == 0]
        if title:
            for i in range(len(bookmarkList)):
                title = self.bookmarkDict.get(bookmarkList[i], '')
                bookmarkList[i] = (bookmarkList[i], title)
        return bookmarkList

    def MacroSetBookmark(self, input):
        bmtype = 0
        try:
            value = int(input)
            self.AddFrameBookmark(value, bmtype)
            return True
        except (TypeError, ValueError):
            if type(input) not in (tuple, list):
                return False
            try:
                values = [int(item) for item in input]
            except (TypeError, ValueError):
                return self.MacroSetBookmark2(input)
            lastindex = len(values) - 1
            for i, value in enumerate(values):
                if i != lastindex:
                    self.AddFrameBookmark(value, bmtype, refreshProgram=False)
                else:
                    self.AddFrameBookmark(value, bmtype, refreshProgram=True)
            return True
        return False

    def MacroSetBookmark2(self, input):
        bmtype = 0
        try:
            value, title = input
            value = int(vaue)
            title = str(title).strip()
            self.bookmarkDict[value] = title
            if not title:
                del self.bookmarkDict[value]
            self.AddFrameBookmark(value, bmtype)
            return True
        except (TypeError, ValueError):
            if type(input) not in (tuple, list):
                return False
            try:
                items = [(int(value), str(title)) for value, title in input]
            except (TypeError, ValueError):
                return False            
            lastindex = len(items) - 1
            for i, item in enumerate(items):
                value, title = item
                title = title.strip()
                self.bookmarkDict[value] = title
                if not title:
                    del self.bookmarkDict[value]
                if i != lastindex:
                    self.AddFrameBookmark(value, bmtype, refreshProgram=False)
                else:
                    self.AddFrameBookmark(value, bmtype, refreshProgram=True)
            return True
        return False
        
    def MacroGetSliderSelections(self):
        return self.GetSliderSelections(self.invertSelection)

    def _x_MacroGetAvs2aviDir(self):
        return self.options['avs2avidir']

    def _x_MacroSetAvs2aviDir(self, exename):
        if os.path.isfile(exename):
            self.options['avs2avidir'] = exename
            return True
        return False

    def MacroGetSliderInfo(self, index=None):
        script, index = self.getScriptAtIndex(index)
        self.UpdateScriptTagProperties(script)
        #~ self.UpdateScriptAVI(script, forceRefresh=True)
        data = self.createUserSliders(script, parseonly=True)
        info = []
        for text, values in data:
            if values is None:
                info.append((text, values))
                continue
            label, minval, maxval, val, nDecimal, step = values
            #~ if step is None:
                #~ if nDecimal == 0:
                    #~ step = 1
                #~ else:
                    #~ step = 1/(nDecimal*10.0)
            #~ count = int((maxval - minval) / step)
            if step is None:
                step = 1/float(10**nDecimal)
            else:
                step = float(step)
            count = int(round((maxval - minval) / step + 1))
            numlist = [minval,] + map(lambda x: step*x + minval, range(1, count)) #+ [maxval,]
            if nDecimal == 0:
                numlist = [int(x) for x in numlist]
            info.append((text, label, numlist, nDecimal))
        return info

    def ExecuteMacro(self, macrofilename='', return_env=False):
        class AvsP_functions:
            # Text setting and retrieving
            InsertText = self.InsertText
            SetText = self.MacroSetText
            #~ ReplaceText = self.MacroReplaceText
            GetText = self.MacroGetText
            GetSelectedText = self.MacroGetSelectedText
            GetSourceString = self.GetSourceString
            GetPluginString = self.GetPluginString
            GetFilename = self.MacroGetFilename
            GetSaveFilename = self.MacroGetSaveFilename
            GetDirectory = self.MacroGetDirectory
            GetTextEntry = self.MacroGetTextEntry
            WriteToScrap = self.MacroWriteToScrap
            GetScrapText = self.MacroGetScrapText
            # Program tab control
            NewTab = self.NewTab
            CloseTab = self.CloseTab
            SelectTab = self.SelectTab
            #~ GetTabFilename = self.MacroGetTabFilename
            GetTabCount = self.MacroGetScriptCount
            GetCurrentTabIndex = self.MacroGetCurrentIndex
            GetScriptFilename = self.MacroGetScriptFilename
            # File opening and saving
            OpenFile = self.OpenFile
            SaveScript = self.MacroSaveScript
            SaveScriptAs = self.SaveScript
            IsScriptSaved = self.MacroIsScriptSaved
            # Video related functions
            ShowVideoFrame = self.MacroShowVideoFrame
            ShowVideoOffset = self.MacroShowVideoOffset
            UpdateVideo = self.MacroUpdateVideo
            HideVideoWindow = self.HidePreviewWindow
            #~ ToggleVideoWindow = self.MacroToggleVideoWindow
            GetFrameNumber = self.GetFrameNumber
            GetVideoWidth = self.MacroGetVideoWidth
            GetVideoHeight = self.MacroGetVideoHeight
            GetVideoFramerate = self.MacroGetVideoFramerate
            GetVideoFramecount = self.MacroGetVideoFramecount
            RunExternalPlayer = self.MacroRunExternalPlayer
            SaveImage = self.MacroSaveImage
            # Bookmarks
            GetBookmarkList = self.MacroGetBookmarkFrameList
            SetBookmark = self.MacroSetBookmark
            GetSelectionList = self.MacroGetSliderSelections
            # Miscellaneous
            MsgBox = self.MacroMsgBox
            ProgressBox = self.MacroProgressBox
            #~ GetAvs2aviDir = self.MacroGetAvs2aviDir
            #~ SetAvs2aviDir = self.MacroSetAvs2aviDir
            GetSliderInfo = self.MacroGetSliderInfo
            #~ UpdateFunctionDefinitions = self.UpdateFunctionDefinitions
            ExecuteMenuCommand = self.MacroExecuteMenuCommand
            IsMenuChecked = self.MacroIsMenuChecked
            GetWindow = staticmethod(lambda: self)
        avsp = AvsP_functions()
        if return_env:
            return avsp
        os.chdir(self.programdir)
        if os.path.isfile(macrofilename):
            try:
                #~ execfile(macrofilename, {'avsp':AvsP_functions}, {})
                # Read the macro text
                f = open(macrofilename)
                #~ macroLines = f.readlines()
                txt = f.read()
                f.close()
                macroLines = txt.split('\n')
                # Check for syntax errors (thows SyntaxError exception with line number)
                try:
                    compile('\n'.join(macroLines+['pass']), macrofilename, 'exec')
                except SyntaxError as e:
                    if not str(e).startswith("'return' outside function"):
                        raise
                # Wrap the macro in a function (allows top-level variables to be treated "globally" within the function)
                lineList = []
                while macroLines and macroLines[0].lstrip().startswith('#'):
                    lineList.append(macroLines.pop(0))
                lineList += ['def AvsP_macro_main():'] + ['\t%s' % line for line in macroLines] + ['global last\nlast = AvsP_macro_main()']
                macrotxt = '\n'.join(lineList)
                #~ macrotxt = '\n'.join(macroLines)
                # Execute the macro
                self.macroVars['avsp'] = AvsP_functions
                exec macrotxt in self.macroVars, {}
            except:
                extra = ''
                for line in traceback.format_exc().split('\n'):
                    if line.endswith('in AvsP_macro_main'):
                        try:
                            linenumber = int(line.split(',')[1].split()[1]) - 1
                            extra = ' (%s, line %i)' % (os.path.basename(macrofilename), linenumber)
                        except:
                            pass
                        break
                wx.MessageBox('%s\n\n%s%s' % (_('Error in the macro:'), sys.exc_info()[1], extra), 
                              _('Error'), style=wx.OK|wx.ICON_ERROR)
        else:
            wx.MessageBox(_("Couldn't find %(macrofilename)s") % locals(), _('Error'), style=wx.OK|wx.ICON_ERROR)
    
    def RenameMacro(self, menu):
        for menuItem in menu.GetMenuItems():
            if menuItem.IsCheckable():
                id = menuItem.GetId()
                macrofilename = self.macrosImportNames[id]
                newname = macrofilename
                if menuItem.IsChecked():
                    newname = newname.replace('ccc', 'CCC')
                    newname = newname.replace('rrr', 'RRR')
                else:
                    newname = newname.replace('CCC', 'ccc')
                    newname = newname.replace('RRR', 'rrr')
                if newname != macrofilename:
                    try:
                        os.rename(macrofilename, newname)
                    except WindowsError:
                        pass
                    
class MainApp(wxp.App):
    def OnInit(self):
        self.frame = MainFrame()
        self.SetTopWindow(self.frame)
        return True

def main():
    try:
        redirect_flag = True
        if __debug__:
            redirect_flag = False
        #~ app = MainApp(redirect_flag, name='AvsP')
        app = MainApp(redirect_flag)
        app.MainLoop()
    except SystemExit:
        sys.exit(0)

if __name__ == '__main__':
    main()
