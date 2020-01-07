# AGC_Python  
为了方便阅读，必须要写好一个**ReadMe**  
其实只有一个文件就是***Dashplot***文件夹，其余两个是测试用的，没用  
1. **AGC_Pdgdata_man_made**是用来创建人为模拟的机组数据：
> 可以给定参数：机组的延迟时间，调节速率，机组抖动等
2. **AGCanalyse_Main**是自动化运行文件，兼顾画图程序，主要调用webservice接口和编撰的函数
3. **FIGUREplot**是画图程序，内置两种画图方式：
> plotly方式，为了便于快速画图，减少重复性工作而设置的面向对象画图，将画图程序转变为更少的业务数据即可；[pyecharts](http://pyecharts.org/#/)是百度开发[echarts](https://echarts.apache.org/zh/index.html)兼容Python的画图程序。此两种程序均可以进行新的定制化函数。
4. **AGCanalyse**中放置了主要的分析函数：详情可参见内置Read.md  
5. **ui_4_calculate**是一个非常简单的小程序，为了给现场运行人员统计储能未跟随指令数据
谢谢阅读
