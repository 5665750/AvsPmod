value = avsp.GetTextEntry([_('Choose a frame step or a number of intervals'),
                           _('Frame step'), _('Number of intervals')],
                            '', _('Bookmarks at Intervals'), 'sep', width=100)
if any(value):
    totalframes = avsp.GetVideoFramecount()
    step = float(value[0]) if value[0] else totalframes / float(value[1])
    bm = 0
    while bm < totalframes - 1:
        avsp.SetBookmark(bm)
        bm += step
