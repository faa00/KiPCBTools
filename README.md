# KiPCBTools
为解决Kicad内置功能缺陷而编写的插件的仓库

# FreeDiffPair 
**自由角度差分对生成器  /  Free Angle Differential Pair Generator**

BUG：
> - 等待反馈 / waiting...

使用方法
> 0. 插件严格要求输入线段：所选的差分对必须足够平行、所选的单端线必须是完全连续的(唯一折线)。
> 1. 选择一段差分对 和 与差分对之一连接的一段或多段单端线，
> 2. 使用插件将生成基于单端线的另一侧差分线。
> 3. 本插件仅针对正常线段设计，仅满足正常的需求，且还在测试阶段。

How to use
> 0. The plug-in strictly requires the input tracks: the selected differential pair must be sufficiently parallel, and the selected single-ended tracks must be completely continuous(Unique polyline).
> 1. Select a differential pair and one or more single-ended tracks connected to one of the differential pairs,
> 2. Using the plug-in will generate the other side differential tracks based on the single-ended tracks.
> 3. This plug-in is only designed for normal layout, only normal requirements, and is still in the testing stage. 

效果参考 / Demo
> <img src="https://github.com/user-attachments/assets/4a24ec38-2c23-4e1e-98a1-fdd1b098aaf4" width="480px">  

基本演示 / Example
> 1. 输入线段基本模型 / Input tracks basic template
> 	<img src="https://github.com/user-attachments/assets/61a57215-92d1-4079-9f92-c1afc8e45930" width="480px">

> 2. 所选区域头和尾都有差分对 / differential pairs on both ends
> 	<img src="https://github.com/user-attachments/assets/9d40940b-b2c4-40a0-bb3a-05e4a244b43f" width="480px">

> 3. 所选区域仅头部有差分对 / only one differential pair
> 	<img src="https://github.com/user-attachments/assets/8ae0bc44-3d5b-4bde-a8d1-9847c4459814" width="480px">   
