from typing import List, Tuple
import pcbnew

from .TrackExport import (
    Polyline2D,
    TPoint2i,
    ExportInfo,
    ExportInfo_Result,
    ExportPoint,
    ExportPoint_Result,
    ExportLine,
    ExportLine_Result,
)

from .include import G_PLUGIN_LOG_FILE


from .logger import getLogger


from .mathLib import (
    G_ANGLE_RAD_TOLERANCE,
    G_RAD_180_DEG,
    Rad,
    Vec2D,
)

from .kiLib import PY_PCB_TRACK, XY2KiVECTOR2I, make_PCB_TRACK, make_SHAPE_CIRCLE  # noqa: F401
from .kiLib import toKiUnit, fromKiUnit  # noqa: F401

logger = getLogger("vec-solver")
logger.addFileHandler(G_PLUGIN_LOG_FILE)


class VecList2D:
    def __init__(self) -> None:
        self._i: int = 0
        self._vecList: List[Vec2D] = []

    def GetList(self):
        return self._vecList

    def Append(self, vec: Vec2D):
        self._vecList.append(vec)

    def Count(self):
        return len(self._vecList)

    def pMoveStart(self):
        self._i = 0

    def pMoveEnd(self):
        self._i = self.Count() - 1

    def pMoveNext(self):
        if self._i >= self.Count() - 1:
            return False
        self._i += 1
        return True

    def pMovePrev(self):
        if self._i <= 0:
            return False
        self._i -= 1
        return True

    def pGet(self):
        return self._i

    def pSet(self, p: int):
        if self._i >= self.Count():
            raise OverflowError
        if self._i <= 0:
            raise ValueError
        self._i = p

    def GetCurrent(self):
        return self._vecList[self._i]

    def __str__(self) -> str:
        return f"<{self.__class__.__name__} 0x{id(self):X} vec:{self.Count()}>"

    def __iter__(self):
        return self._vecList.__iter__()


def MakeVec2D(xy1xy2: Tuple[TPoint2i, TPoint2i]):
    ptStart, ptEnd = xy1xy2
    x = ptEnd.x - ptStart.x
    y = ptEnd.y - ptStart.y
    vec = Vec2D(x, y)
    vec.SetBias([Vec2D(ptStart.x, ptStart.y)])
    return vec


def PolylineToVecList(pl: Polyline2D):
    mvec = VecList2D()

    logger.info("")
    logger.info(f"{PolylineToVecList.__name__}():")

    # 移动线段指针到开头
    pl.pMoveStart()

    logger.info("折线向量化:")
    loop_break = pl.GetPointCount() + 2
    while True:
        loop_break -= 1
        assert loop_break > 0, "循环保护(构建向量时超出最大循环次数)"

        line = pl.GetCurrent()

        # 设计上不该出现这种情况 用于修正静态类型检查(排除None类型)
        assert line is not None, f"失败(只有{pl.GetPointCount()}个端点的非法折线)"

        # 构建向量 加入集合向量
        vec = MakeVec2D(line)
        mvec.Append(vec)
        logger.info(f"  +向量{mvec.Count()} {vec}")

        if pl.pMoveNext() is False:
            break

    return mvec


G_RAD_P90DEG = Rad.fromDeg(90)
G_RAD_N90DEG = Rad.fromDeg(-90)


def CheckPairPolar(
    referVec: Vec2D,
    diffPt2: Tuple[TPoint2i, TPoint2i],
    rad_tolerance=G_ANGLE_RAD_TOLERANCE,
):
    logger.info("")
    logger.info(f"{CheckPairPolar.__name__}():")

    diffVec = MakeVec2D(diffPt2)
    logger.info("检查输入差分对:")
    logger.info(f"  参考 {referVec}")
    logger.info(f"  差分 {diffVec}")

    ret = Vec2D.isParallel(diffVec, referVec, 0.000001)
    assert ret == 1 or ret == -1, "错误(起点差分对不平行)"

    if ret == -1:
        diffVec = MakeVec2D((diffPt2[1], diffPt2[0]))

    logger.info(f"  精度 {Vec2D.GetIncludedAngle(diffVec, referVec).toDegFloat():+.12f}(deg)")
    pair_distance = Vec2D.GetParallelDistance(diffVec, referVec)
    logger.info(f"  间距 {pair_distance:+}(unit)")

    assert pair_distance != 0, "错误(差分对(头)间距为零)"

    return ret, pair_distance


def GenerateNewPointList(
    sVecList: VecList2D,
    vec_distance: int,
):
    logger.info("")
    logger.info(f"{GenerateNewPointList.__name__}():")

    vec_rotate = G_RAD_P90DEG if vec_distance > 0 else G_RAD_N90DEG
    logger.info("旋转极型:")
    logger.info(f"  {vec_rotate}")

    # 重置单端向量表指针
    sVecList.pMoveStart()

    def GetDiffLine(vec: Vec2D, distance: int | float, rotate: Rad):
        # 垂向量 原向量旋转±90度后调整长度 长度必须去除负号
        vec_r90_dis = vec.Rotate(rotate).SetNorm(abs(distance))
        # 差分向量只需要计算起点 = 原向量偏置(头) + 垂向量
        ptStart = (vec.bias + vec_r90_dis).withBias
        # 基于单端向量构建差分向量
        vec_vdiff = vec.Clone()
        vec_vdiff.SetBias([ptStart])

        return vec_vdiff

    def GetJunction(a, b):
        pt = Vec2D.GetLinearJunction(a, b)
        assert pt is not None, "错误(两条虚拟差分线不存在线性交点)"
        return pt

    # 从单端向量表转换指定距离的差分向量表
    logger.info("构造差分向量表:")
    vecList = VecList2D()
    for v in sVecList:
        vec = GetDiffLine(v, vec_distance, vec_rotate)
        vecList.Append(vec)
        logger.info(f"  +向量{vecList.Count()} {vec}")

    # 导出有序交点表
    ptList = VecList2D()
    logger.info("计算多段差分交点:")
    loop_break = vecList.Count() + 2
    while True:
        loop_break -= 1
        assert loop_break > 0, "循环保护(构建向量时超出最大循环次数)"
        # 获取当前向量
        vec1 = vecList.GetCurrent()
        # 后移向量表指针 到结尾时无法移动 增加终点 退出循环
        if vecList.pMoveNext() is False:
            # 增加终点 末尾向量的结束点
            ptList.Append(vec1.withBias)
            break
        # 获取后一个向量 指针已经后移
        vec2 = vecList.GetCurrent()

        pt2f = GetJunction(vec1, vec2)
        ptList.Append(vec=pt2f)
        logger.info(f"  +交点{ptList.Count()} ({pt2f.x},{pt2f.y})")

        continue

    return ptList


def InstanceNewDiff(
    ptList: VecList2D,
    diffStart: Tuple[TPoint2i, TPoint2i],
    diffEnd: Tuple[TPoint2i, TPoint2i] | None,
    info: ExportInfo_Result,
    board: pcbnew.BOARD,
):
    logger.info("")
    logger.info(f"{InstanceNewDiff.__name__}():")

    # 转换差分折线 开始于参考差分线(头)的起点
    pl = Polyline2D(diffStart[0])
    logger.info("构造差分折线:")
    logger.info(f"  +起点{pl.GetPointCount()} {diffStart[0]}")
    pl.AddPoint(diffStart[1])
    logger.info(f"  +端点{pl.GetPointCount()} {diffStart[1]}")

    # 交点列表的结构是 新生成差分线不包括起点 仅包括 所有交点 + 终点
    skip_obj = None
    if diffEnd is not None:
        skip_obj = ptList.GetList()[-1]

    for pt in ptList:
        # 如果输入包括结尾参考差分线 需要先把交点列表里的终点去掉
        if pt is skip_obj:
            continue

        # 折线的终点 视为当前遍历交点的上一点
        prvePt = pl.GetEnd()
        assert prvePt.BindCount() == 1, f"错误(非法差分折线 终点绑定了{prvePt.BindCount()}个线路)"
        # 应用交点到折线终点
        prvePt.SetXY(pt.x, pt.y)

        # 构建PCB线路 以交点为起点 终点任意
        pobj = PY_PCB_TRACK((board, pt, pt + Vec2D(1, 0)))
        pobj.setWidth(info.width)
        pobj.SetLayer(info.layer)

        # 插入PCB线路
        pobj.AddTo(board)

        # 构建端点绑定信息
        StartBind = TPoint2i.bindInfo(pobj, TPoint2i.TRACK_START_POINT)
        EndBind = TPoint2i.bindInfo(pobj, TPoint2i.TRACK_END_POINT)

        # 把起点 绑定到折线终点
        prvePt.AppendBind(StartBind)
        # logger.info(f"   更新{pl.GetPointCount()} {prvePt}")

        # 把终点 绑定到新的端点 后插入多边形末尾
        thisPt = TPoint2i(pt.x, pt.y, EndBind)
        pl.AddPoint(thisPt)
        logger.info(f"  +端点{pl.GetPointCount()} {thisPt}")

        continue

    # 完成差分折线 结束于参考差分线(头)的终点
    if diffEnd is not None:
        # 折线的终点 视为参考差分线(尾)的起点
        endPt = pl.GetEnd()
        assert endPt.BindCount() == 1, f"错误(非法差分折线 终点绑定了{endPt.BindCount()}个线路)"

        # 参考差分线(尾)的起点 绑定到折线终点
        endPt.AppendBind(diffEnd[0].GetBindFirst())
        logger.info(f"  更新终点 {endPt}")
        # 参考差分线(尾)的终点 插入多边形末尾
        pl.AddPoint(diffEnd[1])
        logger.info(f"  +终点{pl.GetPointCount()} {diffEnd[1]}")

    # 更新折线内所有端点到绑定的PCB线路
    logger.info("差分线段列表:")
    for pt in pl.GetList():
        logger.info(f" 更新线路 {pt}")
        pt.Update()

    return pl


def AddCuShapeTrackLock(
    pl: Polyline2D,
    info: ExportInfo_Result,
    board: pcbnew.BOARD,
):
    logger.info("")
    logger.info(f"{AddCuShapeTrackLock.__name__}():")

    width = info.width - toKiUnit(0.05)

    logger.info("增加线路锁定形状:")

    for pt in pl.GetList():
        xy = Vec2D(pt.x, pt.y)
        kobj = make_SHAPE_CIRCLE(
            board,
            info.layer,
            xy,
            size=width,
        )
        board.Add(kobj)
        logger.info(f"  +CIRCLE {xy}")


def PluginMain(board: pcbnew.BOARD):
    def GetInputTracks(board):
        ret: List[PY_PCB_TRACK] = []
        for track in board.GetTracks():
            if not isinstance(track, pcbnew.PCB_TRACK):
                raise TypeError
            if track.IsSelected():
                t = PY_PCB_TRACK(track)
                ret.append(t)
        return ret

    inputList: List[PY_PCB_TRACK] = GetInputTracks(board)

    if len(inputList) < 3:
        return

    # 解析PCB上选择的线路 线路 > 端点 > 折线
    infoResult = ExportInfo(inputList)
    pointResult = ExportPoint(inputList)
    lineResult = ExportLine(pointResult)

    # 单端折线 转换到向量表
    vecList = PolylineToVecList(lineResult.sReferPolyline)

    # 校验 起始侧 参考差分线和单端折线 的差分关系正确性
    vecList.pMoveStart()
    polarStart, distanceStart = CheckPairPolar(
        vecList.GetCurrent(),
        lineResult.dReferStart,
    )
    if polarStart == 1:
        diffStart = lineResult.dReferStart
    else:
        diffStart = (lineResult.dReferStart[1], lineResult.dReferStart[0])

    # 校验 结束侧 参考差分线和单端折线 的差分关系正确性

    if lineResult.dReferEnd is not None:
        vecList.pMoveEnd()
        polarEnd, distanceEnd = CheckPairPolar(
            vecList.GetCurrent(),
            lineResult.dReferEnd,
        )
        assert distanceStart - distanceEnd < 0.5, f"失败(头尾的差分间距不一致) 间距差={distanceStart - distanceEnd}"

        if polarEnd == 1:
            diffEnd = lineResult.dReferEnd
        else:
            diffEnd = (lineResult.dReferEnd[1], lineResult.dReferEnd[0])
    else:
        diffEnd = None

    # 有符号差分线距 负号代表参考差分线在单端折线的逆角度方向
    distance = int(distanceStart)

    # 通过差分线距 生成新差分折线交点列表
    ptList = GenerateNewPointList(vecList, distance)

    # 更新交点 新建PCB线路
    refer_pl = lineResult.sReferPolyline
    diff_pl = InstanceNewDiff(
        ptList,
        diffStart,
        diffEnd,
        infoResult,
        board,
    )

    # 增加交点锁定 新建PCB形状
    AddCuShapeTrackLock(refer_pl, infoResult, board)
    AddCuShapeTrackLock(diff_pl, infoResult, board)

    return
