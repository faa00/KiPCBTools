import math
from .include import G_PLUGIN_LOG_FILE
from .logger import getLogger
from .mathLib import Vec2D
from .kiLib import PY_PCB_TRACK

from typing import List, Tuple

logger = getLogger("track-export")
logger.addFileHandler(G_PLUGIN_LOG_FILE)


class TPoint2i:
    TRACK_END_POINT = 1
    TRACK_START_POINT = -1

    class bindInfo:
        def __init__(self, pyTrack: PY_PCB_TRACK, ptype: int):
            self.obj: PY_PCB_TRACK = pyTrack
            self.ptype: int = ptype

    def __init__(self, x: int | float, y: int | float, bind: bindInfo) -> None:
        # 端点的坐标
        self._x: int = int(x)
        self._y: int = int(y)
        # 端点绑定的线路列表
        self._bindList: List[TPoint2i.bindInfo] = [bind]

    # fmt:off

    def SetXY(self,x:int|float,y:int|float):
        self._x = int(x)
        self._y = int(y)

    @property
    def x(self): return self._x

    @x.setter
    def x(self,x:int|float): self._x = int(x)

    @property
    def y(self): return self._y

    @y.setter
    def y(self,y:int|float): self._y = int(y)

    # fmt:on

    def AppendBind(self, i: bindInfo):
        if i in self._bindList:
            return False
        self._bindList.append(i)
        return True

    def RemoveBind(self, i: bindInfo):
        if i not in self._bindList:
            return False
        self._bindList.remove(i)
        return True

    def HasBind(self, obj: PY_PCB_TRACK, ptyle: int):
        for i in self._bindList:
            if (i.obj is obj) and (i.ptype == ptyle):
                return True
            continue
        return False

    def BindCount(self):
        return len(self._bindList)

    def GetBindList(self):
        return self._bindList

    def GetBindFirst(self):
        return self._bindList[0]

    # Update all bound line objects
    def Update(self):
        if len(self._bindList) == 0:
            logger.error(f"{self} endpoint does not bind any line segments and will not perform any operation")
            return

        for track in self._bindList:
            tobj = track.obj
            ptype = track.ptype
            # Endpoint type endpoint
            if ptype == self.TRACK_END_POINT:
                logger.info(f"(0x{id(tobj):X}).SetEnd   ({self._x:+}, {self._y:+})")
                tobj.SetEnd(Vec2D(self._x, self._y))
                continue
            # End point type starting point
            if ptype == self.TRACK_START_POINT:
                logger.info(f"(0x{id(tobj):X}).SetStart ({self._x:+}, {self._y:+})")
                tobj.SetStart(Vec2D(self._x, self._y))
                continue
            logger.error(f"<0x{id(tobj):X}> Non-existent endpoint type({ptype}) will perform no operation.")
        return

    def __str__(self) -> str:
        return f"<{self.__class__.__name__} 0x{id(self):X} XY=({self._x:+},{self._y:+}) bind:{len(self._bindList)}>"

    def __repr__(self) -> str:
        return self.__str__()

    def XYEQ(self, x: int, y: int):
        return self.x == x and self.y == y


class Polyline2D:
    def __init__(self, start: TPoint2i) -> None:
        self._i: int = 1
        self._ptList: List[TPoint2i] = [start]

    def Reverse(self):
        self._ptList.reverse()

    def GetList(self):
        return self._ptList

    def GetPointCount(self):
        return len(self._ptList)

    def GetStart(self):
        return self._ptList[0]

    def GetEnd(self):
        return self._ptList[-1]

    def AddPoint(self, pt: TPoint2i):
        if pt in self._ptList:
            return False
        self._ptList.append(pt)
        return True

    def RemovePoint(self, pt):
        if pt not in self._ptList:
            return False
        self._ptList.remove(pt)
        return True

    def _GetLine(self, i: int):
        return self._ptList[i - 1], self._ptList[i]

    def GetCurrent(self):
        if self.GetPointCount() <= 1:
            return None
        return self._GetLine(self._i)

    def GetPrev(self):
        if self._i <= 1:
            return None
        return self._GetLine(self._i - 1)

    def GetNext(self):
        if self._i >= self.GetPointCount() - 1:
            return None
        return self._GetLine(self._i + 1)

    def pMoveNext(self):
        if self._i >= self.GetPointCount() - 1:
            return False
        self._i += 1
        return True

    def pMovePrev(self):
        if self._i <= 1:
            return False
        self._i -= 1
        return True

    def pMoveStart(self):
        self._i = 1

    def pMoveEnd(self):
        self._i = self.GetPointCount() - 1

    def pGet(self):
        return self._i

    def pSet(self, p: int):
        if self._i >= self.GetPointCount():
            raise OverflowError
        if self._i <= 1:
            raise ValueError
        self._i = p

    def __str__(self) -> str:
        return f"<{self.__class__.__name__} 0x{id(self):X} point:{self.GetPointCount()}>"

    def __repr__(self) -> str:
        return self.__str__()

    def __iter__(self):
        index = 1
        while not index >= len(self._ptList):
            yield self._GetLine(index)
            index += 1


class ExportInfo_Result:
    def __init__(
        self,
        layer: int,
        width: int,
    ) -> None:
        self.layer: int = layer
        self.width: int = width


def ExportInfo(pyTrackList: List[PY_PCB_TRACK]):
    #
    logger.info("")
    logger.info(f"{ExportInfo.__name__}():")

    logger.info("Get line physical information:")
    layer = pyTrackList[0].GetLayer()
    width = pyTrackList[0].GetWidth()
    for track in pyTrackList[1:]:
        ret_layer = track.GetLayer()
        ret_width = track.GetWidth()
        if layer != ret_layer:
            assert "failure (different lines)"
        if width != ret_width:
            assert "Failed (line width is inconsistent)"

    logger.info(f"  copper layer {pyTrackList[0].GetLayerName()}({layer})")
    logger.info(f"  width {width}(unit)")
    return ExportInfo_Result(layer, width)


class ExportPoint_Result:
    def __init__(
        self,
        diff_tlist: List[Tuple[TPoint2i, TPoint2i]],
        share_ptlist: List[TPoint2i],
        share_ep_2pt: Tuple[TPoint2i, TPoint2i],
    ) -> None:
        self.diffList: List[Tuple[TPoint2i, TPoint2i]] = diff_tlist
        self.shareList: List[TPoint2i] = share_ptlist
        self.shareEp2x: Tuple[TPoint2i, TPoint2i] = share_ep_2pt


def ExportPoint(pyTrackList: List[PY_PCB_TRACK]):
    #
    all_point_list: List[TPoint2i] = []
    logger.info("")
    logger.info(f"{ExportPoint.__name__}():")

    def AddPoint(x, y, ptInfo: TPoint2i.bindInfo, ptList: List[TPoint2i]):
        for point in ptList:
            # The endpoint exists and the bound line
            if point.XYEQ(x, y):
                point.AppendBind(ptInfo)
                logger.info(f"  bind to   {point}")
                return
            continue
        # Add to cache binding line
        obj = TPoint2i(x, y, ptInfo)
        ptList.append(obj)
        logger.info(f"  new endpoint {obj}")

    # When the endpoint of all line sections is the same point,
    # it is bound to the corresponding object
    logger.info(f"Input line endpoint check(x{len(pyTrackList)}):")
    for track in pyTrackList:
        logger.info(f"  {track}")
        # From the starting point of the line
        ptStart = track.GetStart()
        AddPoint(
            ptStart.x,
            ptStart.y,
            TPoint2i.bindInfo(track, TPoint2i.TRACK_START_POINT),
            all_point_list,
        )
        # Import the end point of the route
        ptEnd = track.GetEnd()
        AddPoint(
            ptEnd.x,
            ptEnd.y,
            TPoint2i.bindInfo(track, TPoint2i.TRACK_END_POINT),
            all_point_list,
        )

    logger.info("Endpoint capture list:")
    indep_point_list: List[TPoint2i] = []
    share_point_list: List[TPoint2i] = []

    # Export polyline endpoint list independent line list
    for point in all_point_list:
        logger.info(f"  {point}")
        count = point.BindCount()
        assert count <= 2, "Endpoint is shared by more than two lines."
        if count == 1:
            indep_point_list.append(point)
        elif count == 2:
            share_point_list.append(point)
        continue

    # The differential reference line plus the reference polyline has up to
    # six dangling endpoints (polyline x2 + head differential line x2 + tail
    # differential line x2)
    # At least one differential reference line requires at least
    # four suspended endpoints (multi -segment line X2 + differential line X2)
    assert len(share_point_list) != 0, "Failed (no continuous polyline)"
    assert len(indep_point_list) == 4 or len(indep_point_list) == 6, "Failure (less than four or six suspended endpoints)"

    track_diff_list: List[Tuple[TPoint2i, TPoint2i]] = []

    def FindALine(ptList: List[TPoint2i]):
        ret: Tuple[TPoint2i, TPoint2i] | None = None
        # Find the two ends on the same line in the point list
        for pt1 in ptList:
            for pt2 in ptList:
                # Jump over yourself
                if pt1 is pt2:
                    continue
                # The endpoint is not in the same line, and the differential line is not hit
                if pt1.GetBindFirst().obj is not pt2.GetBindFirst().obj:
                    continue
                # The endpoint attribute cannot be the same (the design should not be the same)
                if pt1.GetBindFirst().ptype == pt2.GetBindFirst().ptype:
                    continue
                # Only record the first line segment found and remove both ends from the input list
                ret = (pt1, pt2)
                ptList.remove(pt1)
                ptList.remove(pt2)
                # Return immediately
                return ret
            continue
        # No line segments found
        return None

    line_count = len(pyTrackList)

    # Export the first differential reference line
    track1d_2pt = FindALine(indep_point_list)
    assert track1d_2pt is not None, "Failed (reference differential line not found)"

    # Insert the first reference line list
    line_count -= 1
    track_diff_list.append(track1d_2pt)
    logger.info("Output reference differential line A:")
    logger.info(f"  {track1d_2pt[0].GetBindFirst().obj}")
    for point in track1d_2pt:
        logger.info(f"  {point}")

    # Export the second differential reference line
    track2d_2pt = FindALine(indep_point_list)
    if track2d_2pt is not None:
        line_count -= 1
        # Insert second reference line list
        track_diff_list.append(track2d_2pt)
        logger.info("Output Reference Differential Line B:")
        logger.info(f"  {track2d_2pt[0].GetBindFirst().obj}")
        for point in track2d_2pt:
            logger.info(f"  {point}")

    # In design, only up to two independent line segments are allowed
    # (head differential line + tail differential line)
    assert FindALine(indep_point_list) is None, "failure (existing excess independent line segment)"

    # Verify the number of polyline endpoints (total input number -
    # reference number of differential lines)
    logger.info(f"Output reference single-ended shared endpoint (x{len(share_point_list)}):")
    for point in share_point_list:
        logger.info(f"  {point}")

    # If there are N polylines in the design, there will be N-1 endpoints.
    assert line_count - 1 == len(share_point_list), "Failed (wrong number of shared endpoints)"

    # The two endpoints of the single - end fold line
    assert len(indep_point_list) == 2, "Failed (too many dangling endpoints)"
    share_endpoint_2pt = indep_point_list[0], indep_point_list[1]

    logger.info(f"Output reference single-ended floating endpoint (x{len(share_endpoint_2pt)}):")
    for point in share_endpoint_2pt:
        logger.info(f"  {point}")

    return ExportPoint_Result(
        track_diff_list,
        share_point_list,
        share_endpoint_2pt,
    )


class ExportLine_Result:
    def __init__(
        self,
        polyline: Polyline2D,
        dReferStart: Tuple[TPoint2i, TPoint2i],
        dReferEnd: Tuple[TPoint2i, TPoint2i] | None,
    ) -> None:
        self.sReferPolyline: Polyline2D = polyline
        self.dReferStart: Tuple[TPoint2i, TPoint2i] = dReferStart
        self.dReferEnd: Tuple[TPoint2i, TPoint2i] | None = dReferEnd


def ExportLine(obj: ExportPoint_Result):
    #
    track_diff_list = obj.diffList
    share_point_list = obj.shareList
    share_enpoint_2pt = obj.shareEp2x

    logger.info("")
    logger.info(f"{ExportLine.__name__}():")

    # Verify reference number of differential lines
    tdiff_count = len(track_diff_list)
    assert tdiff_count == 1 or tdiff_count == 2, "Error (reference differential line does not exist or exceeds supported number)"

    def getLineToPointDistanceSum(line: Tuple[TPoint2i, TPoint2i], pt: TPoint2i):
        d1 = math.sqrt(math.pow(line[0].x - pt.x, 2) + math.pow(line[0].y - pt.y, 2))
        d2 = math.sqrt(math.pow(line[1].x - pt.x, 2) + math.pow(line[1].y - pt.y, 2))
        return int(d1 + d2)

    # Define the first of reference differential lines as the starting
    # point of the starting point is the ending point
    tdiff_start: Tuple[TPoint2i, TPoint2i] = track_diff_list[0]
    tdiff_end: Tuple[TPoint2i, TPoint2i] | None = None
    if len(track_diff_list) == 2:
        tdiff_end = track_diff_list[1]

    ep1 = share_enpoint_2pt[0]
    ep2 = share_enpoint_2pt[1]

    # Get the distance and the distance between the two ends of the
    # differential line of the selection of the endpoint
    # And the smallest endpoint are defined as the starting point of the multi-end line
    ptStart = ep1
    ptEnd = ep2
    if getLineToPointDistanceSum(tdiff_start, ep1) > getLineToPointDistanceSum(tdiff_start, ep2):
        ptStart = ep2
        ptEnd = ep1

    # From the starting point of a single-end fold line
    pl = Polyline2D(ptStart)
    logger.info(f"Input Construct polygon from point list (x{len(share_point_list) + len(share_enpoint_2pt)})构建多边形:")
    logger.info(f"  + starting point {pl.GetPointCount()} {ptStart}")

    # The shared endpoint of the polyline will bind two line objects
    # When you find the opposite endpoint, get the line object
    # To filter the current object to avoid reverse search for endpoints

    loop_break = len(share_point_list) + 2
    black_obj: PY_PCB_TRACK | None = None
    while True:
        # Cycle protection
        loop_break -= 1
        assert loop_break > 0, "Circulation protection (the maximum number of cycles exceeds the maximum cycle when building a folding line)"

        cur_bind: TPoint2i.bindInfo | None = None
        for bind in pl.GetEnd().GetBindList():
            # In terms of design, at most two bound line objects will be traversed.
            # In terms of process, the last used object should be blocked to avoid reverse search
            # The starting point A0 side is the end point A1 and the A1 side is B0 or A0 that cannot be searched for A0, so it must block the line object of A0A1
            if bind.obj is black_obj:
                continue
            cur_bind = bind

        # In terms of design, only one line object is bound to the end point. Shielding is required after the last use. This time there will be no object and the loop should end.
        if cur_bind is None:
            break

        cur_pobj = cur_bind.obj
        cur_ptype = cur_bind.ptype
        cur_point: TPoint2i | None = None
        for pt in share_point_list:
            # If there is a matching opposite endpoint, ptNext will remain None
            if pt.HasBind(cur_pobj, -cur_ptype) is False:
                continue
            # Insert the other endpoint of the line segment
            pl.AddPoint(pt)
            cur_point = pt
            logger.info(f"  +endpoint {pl.GetPointCount()} {pt} → {cur_pobj}")
            break

        # Existing the next end -end point reset loop
        if cur_point is not None:
            black_obj = cur_pobj
            continue

        # Design total number of end points - uninserted end points = number of lines
        assert pl.GetPointCount() - 1 == len(share_point_list), "There is a continuity problem in the input line segment"

        break

    # Insert the final endpoint
    pl.AddPoint(ptEnd)
    logger.info(f"  +end {pl.GetPointCount()} {ptEnd} = {ptEnd.GetBindFirst().obj}")

    logger.info("Output reference single-ended polyline:")
    logger.info(f"  {pl}")

    logger.info("Output Starting Reference Differential Line:")
    logger.info(f"  {tdiff_start[0]},{tdiff_start[1]}")

    if tdiff_end is not None:
        logger.info("The output ends reference differential line:")
        logger.info(f"  {tdiff_end[0]},{tdiff_end[1]} ")

    return ExportLine_Result(
        pl,
        tdiff_start,
        tdiff_end,
    )
