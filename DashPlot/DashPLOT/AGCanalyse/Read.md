>time:  
2019.12.03:  
2020.01.07:add information
2020.04.26:修正readme文件
author : Wangby  
Description : file record  
  
# 主要为代码，并没有相关文件  
主要含有2个文件**Base_analyse.py**,**check_and_deal_data**  
在运行过程中若遇到画图中不含有[chromedriver](https://sites.google.com/a/chromium.org/chromedriver/home)问题，请自行点击链接进行配置  
## Base_analyse.py  
主要为分析文件：包含kp、电池、机组、AGC指令分析  
1. **operation_analyse**是基类，主要传入电站的基本信息以及各个地区共用的函数,见表格：

|方法名 |用途|
|:----:|:----:|
|AGCstrength|AGC指令强度|
|BATstrength|电池运行强度|
|BATstrength_ems|EMS数据算电池运行强度|
|PDGstrength|机组运行考评|
|agc_static|指令及储能联合强度计算|

2. **MX**是蒙西电网的k值计算类,继承基类
3. **GD**是广东电网的k值计算类,其下有不同版本,此外含有一种方法:计算每条指令AGC下机组与储能对完成指令的贡献度
4. **HB**是华北电网的k值计算类,继承基类
5. **JS**是江苏电网的k值计算类,继承基类
6. **cost_perunit**是计算投资收益的类
7. **Heat_analyse**是计算电池热量的类,主要计算连续满功率的持续时间计算参考最高温

## check_and_deal_data  
主要为数据检查和自动从云平台下载功能，接口参见内部文件  
***