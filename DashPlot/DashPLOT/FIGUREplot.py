'''
Created on 2019年7月8日

@author: JesisW
'''
import plotly.graph_objs as go
import numpy as np
import pandas as pd
import plotly
import pyecharts
from pyecharts import options as opts
from pyecharts.render.snapshot import make_snapshot
from snapshot_selenium import snapshot as driver
# path = r'D:\EMScase\代码\仿真结果与原有控制对比.xlsx'
# df = pd.read_excel(path,sheet_name=None,encoding = 'gbk')
# df1 = df['数据0331']
# columnsname = df1.keys()[1:6]
# yaxis = ['y1','y1','y1','y2','y3']
# yname = ['功率/MW','功率/MW','功率/MW','储能功率/MW','SOC']
# legends = [1,2,3,4,5]
# yaxisnum = dict(zip(columnsname,yaxis))
# yaxisname = dict(zip(yaxis,yname))
# legends = dict(zip(columnsname,legends))
# xaxisname = 't'
# colorsX = ['#1f77b4','#8dd3c7','#d62728','#ff7f0e','#fdb462','#fb8072','#80b1d3','#800080','#008D00']

class figplotly():
    '''
    由于经常需要画plotly交互图，因而对该部分进行代码话，自动根据变量名画图
    example:
    path = r'C'
    df = pd.read_csv(path,encoding = 'gbk')
     
    columnsname = df.keys()
    yaxis = ['y1','y2','y3','y4'] # 轴的编号
    yname = ['Agc','Pbat','SOC','机组'] # 轴的名字
    legends = [1,1,2,3] # 图例分组
    yaxisnum = dict(zip(columnsname,yaxis)) # key-value 对应
    yaxisname = dict(zip(yaxis,yname))#
    legends = dict(zip(columnsname,legends))
    xaxisname = 'Time'
    colorsX = ['#1f77b4','#8dd3c7','#d62728','#ff7f0e','#fdb462','#fb8072','#80b1d3','#800080','#008D00']
    '''
    attention = "请给出想要绘制图形的列名'columnsname'\n对应绘制的轴'yaxis'\n对应的轴名'yname'\n分组编号'legends'\n以及横坐标名'xaxisname'"
#     print('----------若使用方法figplotly------------')
#     print(attention)
    def __init__(self,columnsname,yaxis,yname,legends,xaxisname):
        self.columnsname = columnsname
        self.yaxisnum = dict(zip(columnsname,yaxis))
        self.yaxisname = dict(zip(yaxis,yname))
        self.legends = dict(zip(columnsname,legends))
        self.xaxisname = xaxisname
        self.colorsX = ['#1f77b4','#8dd3c7','#d62728','#ff7f0e','#fdb462','#fb8072','#80b1d3','#800080','#008D00']
        
    def Fgplot(self,df):
        columnsname,xaxisname,yaxisnum = self.columnsname,self.xaxisname,self.yaxisnum
        yaxisname,legends,colorsX = self.yaxisname,self.legends,self.colorsX
        trace = []
        length = len(columnsname)
        for i in np.arange(length):
            trace.append(
                (go.Scatter(
                    line = dict(color = colorsX[i],width = 0.5),
                    x = df[xaxisname],
                    y = df[columnsname[i]],
                    mode = 'lines',
                    connectgaps = False,
                    name = columnsname[i],
                    showlegend = True,
                    hoverinfo = 'all',
                    yaxis = yaxisnum[columnsname[i]],
                    legendgroup = legends[columnsname[i]]
                    )
                )
            )
        num = len(set(yaxisnum.values())) # set 函数不允许有重复数据
        layout = go.Layout(
            legend = dict(x = 1.0, xanchor = 'auto', y = 1.03,
                        orientation = 'h'),
            xaxis = dict(
                domain = [0.15,0.85],
                showline=True,
                showgrid=False,
                showticklabels=True,
                linewidth=2,
                ticks='outside',
                tickformat="%Y-%m-%d\n%H:%M:%S",
                tickwidth=2,
                ticklen=5,
                tickfont=dict(
                    family='Arial',
                    size=12,
                    color='rgb(82, 82, 82)',
                ),
                calendar='gregorian',#"%Y-%m-%d %H:%M:%S"
                hoverformat="%Y-%m-%d %H:%M:%S",#%Y-%m-%d %H:%M:%S %L
                rangeslider=dict(
                    visible=True,
                    )
                ),
            margin=dict(
                autoexpand=True,
                l=20,
                r=20,
                t=100,
                ),
            showlegend=True,
            )
        a = [0.15,0.85,0.1,0.9,0.05,0.95]
        for i in np.arange(1,num+1):
            if i%2 == 1:
                layout['yaxis'+str(i)] = dict(
                    title = yaxisname['y'+str(i)],
                    linecolor = colorsX[i],
                    showgrid=False,
                    zeroline=False,     #是否显示基线,即沿着(0,0)画出x轴和y轴
                    showline=True,
                    showticklabels=True,
                    titlefont=dict(color=colorsX[i]),
                    tickfont=dict(color=colorsX[i]),
                    anchor = 'free',
                    overlaying = 'y',
                    side = 'left',
                    position = a[0]
                    )
            else:
                layout['yaxis'+str(i)] = dict(
                    title = yaxisname['y'+str(i)],
                    linecolor = colorsX[i],
                    showgrid=False,
                    zeroline=False,     #是否显示基线,即沿着(0,0)画出x轴和y轴
                    showline=True,
                    showticklabels=True,
                    titlefont=dict(color=colorsX[i]),
                    tickfont=dict(color=colorsX[i]),
                    anchor = 'free',
                    overlaying = 'y',
                    side = 'right',
                    position = a[0]
                    )
            if i == 1:
                layout['yaxis'+str(i)]['overlaying'] = 'free'
            a.remove(a[0])
        fig = go.Figure(data = trace, layout = layout)
        return fig

# fig = Fgplot(df1,columnsname,xaxisname,yaxisnum,yaxisname,legends,colorsX)
    def FgTitle(self,title,source):
        annotations = []
        # Title
        annotations.append(dict(xref='paper', yref='paper', x=0.5, y=1.08,
                                  xanchor='center', yanchor='bottom',
                                  text=title,
                                  font=dict(family='Arial',
                                            size=18,
                                            color='rgba(37,37,37,0.8)'),
                                  showarrow=False))
        # Source
        annotations.append(dict(xref='paper', yref='paper', x=0.5, y=1.05,
                                  xanchor='center', yanchor='top',
                                  text=source,
                                  font=dict(family='Arial',
                                            size=12,
                                            color='rgba(150,150,150,0.8)'),
                                  showarrow=False))
        return annotations
# ano = FgTitle('Agc仿真曲线','云河3月31日')
# fig['layout']['annotations'] = ano
# plot_url = plotly.offline.plot(fig,filename='C:\\Users\\JesisW\\Desktop\\Ha.html')

class figecharts():
    '''
    This file is for daily report
    '''
    # set_global_opts的选项
    # title_opts, legend_opts, tooltip_opts, toolbox_opts, 
    # brush_opts, xaxis_opts, yaxis_opts, visualmap_opts, 
    # datazoom_opts, graphic_opts, axispointer_opts
#     print('----------若使用方法figecharts----------')
#     print('请给出相应的电站序号\n 0:新丰\n 1:云河\n 2:准大\n 3:海丰\n 4:河源\n 5:宣化\n 6:同达\n 7:上都\n 8:平朔\n 9:鲤鱼江\n')
    def __init__(self,i,Agcresult=None,BatResult=None,kpresult=None):
        index_name = ['新丰','云河','准大','海丰','河源','宣化','同达','上都','平朔','鲤鱼江']
        Area =  ['MX' ,'GD',' MX' ,'GD', 'GD', 'HB', 'HB', 'HB', 'HB', 'GD']
        Stationname = ['新丰','云河','海丰','河源','鲤鱼江','恒运','宣化','准大','兴和','上都','平朔','同达']
        Pe = [300,300,1000,600,300,300,300,300,300,600,300,300]
        Pe = dict(zip(Stationname,Pe))
        if Area[i] == 'GD':
            self.Vb = 0.01903
        else:
            self.Vb = 0.015
        self.Pe = Pe[index_name[i]]
        self.Agcresult = Agcresult
        self.BatResult = BatResult
        self.kpresult = kpresult
        
    def figAgc(self,path):
        '''
        path: 文件输出位置
        '''
        Agcresult = self.Agcresult
        if Agcresult is not None:
            Candleline = pyecharts.charts.Kline()
            x_line = Agcresult.index.tolist()
            y_line = Agcresult.apply(lambda x:[x['Beg'],x['End'],x['Min'],x['Max']], axis = 1).tolist()
            # a.apply(func)函数是对每一行(axis=1)或每一列进行这个函数‘func’操作
            AGCcandle = (Candleline
                        .add_xaxis(x_line)
                        .add_yaxis('AGC',
                                   y_line)
                        .set_global_opts(
                            title_opts = opts.TitleOpts(title='AGC统计',
                                                        pos_left='center'
                                                        ),
                            xaxis_opts = opts.AxisOpts(name = '第k时段',
                                                       is_show=True,
                                                       name_location='middle',
                                                       name_gap=25
                                                       ),
                            yaxis_opts = opts.AxisOpts(name = 'Agc功率/MW',
                                                       is_show=True,
                                                       name_location='middle',
                                                       name_gap=40
                                                       ),
                            legend_opts = opts.LegendOpts(pos_left='right')
                            )
            
            )
            make_snapshot(driver, AGCcandle.render(),path+'\\蜡烛图.png')
            # kline.render('')# 用来展示图的
            Line = pyecharts.charts.Line()
            y_line = pd.DataFrame(columns=['速度','标准速度'])
            Agcresult.loc[Agcresult['SaDt'] == 0,'SaDt'] = 10000
            Agcresult.loc[Agcresult['Num'] == 0,'Num'] = 10000
            y_line['速度'] = Agcresult['SaD']/Agcresult['SaDt']*60
            y_line['标准速度'] = self.Vb*self.Pe
            VLine = (Line
                    .add_xaxis(x_line)
                    .add_yaxis('需求调节速度',
                               y_line['速度'].tolist(),
                               symbol='circle',
                               symbol_size = 5,
                               label_opts = opts.LabelOpts(is_show=False),
                               linestyle_opts = opts.LineStyleOpts(width=3))# 这个Label是控制图中数据的显示与否
                    .add_yaxis('标准调节速度',
                               y_line['标准速度'].tolist(),
                               symbol='circle',
                               symbol_size = 5,
                               label_opts = opts.LabelOpts(is_show=False),
                               linestyle_opts = opts.LineStyleOpts(width=3))
                    .set_global_opts(
                        title_opts=opts.TitleOpts(title='需求调节速度',
                                                  pos_left='center'
                                                  ),
                        xaxis_opts = opts.AxisOpts(name = '第k时段',
                                               is_show=True, # 这个事控制轴名的
                                               name_location='middle',
                                               name_gap=25
                                               ),
                        yaxis_opts = opts.AxisOpts(name = '速率(MW/min)',
                                               is_show=True,
                                               name_location='middle',
                                               name_gap=40
                                               ),
                        legend_opts = opts.LegendOpts(pos_left='right')
                        )
                )
            make_snapshot(driver, VLine.render(),path+'\\调节速度.png')
            Bar = pyecharts.charts.Bar()
            Line = pyecharts.charts.Line()
            y_line = Agcresult['Ret'].tolist()
            Zhefan = (Bar
                        .add_xaxis(x_line)
                        .add_yaxis('折返次数',
                                   y_line,
                                   yaxis_index =0,
                                   label_opts = opts.LabelOpts(is_show=False))
                        .extend_axis(
                            yaxis=opts.AxisOpts(
                                name='折返比例',
                                min_=0,
                                max_=100,
                                position='right',
                                name_location='middle',
                                name_gap=23
                                )
                            )
                        .set_global_opts(
                            title_opts = opts.TitleOpts(title='折返情况',pos_left='center'),
                            yaxis_opts = opts.AxisOpts(
                                name = '折返次数',
                                position='left',
                                name_location='middle',
                                name_gap=20,
                                max_=max(y_line),
                                min_=min(y_line)
                                ),
                            xaxis_opts = opts.AxisOpts(
                                name = '第k时段',
                                name_location='middle',
                                name_gap=25
                                ),
                            legend_opts = opts.LegendOpts(pos_left='right')
                            )
                        )
            
            line = (Line
                    .add_xaxis(x_line)
                    .add_yaxis(
                        '折返比例',
                        (Agcresult['Ret']/Agcresult['Num']*100).tolist(),
                        yaxis_index = 1,
                        symbol = 'circle',
                        symbol_size =5,
                        label_opts = opts.LabelOpts(is_show=False),
                        linestyle_opts = opts.LineStyleOpts(width=3)
                        )
                    )
            Zhefan.overlap(line)
            Rmixline = pyecharts.charts.Grid()
            Rmixline.add(Zhefan, opts.GridOpts(pos_left='5%',pos_right='5%'),is_control_axis_index = True)
            make_snapshot(driver, Rmixline.render(),path+'\\折返.png')
            
            Line = pyecharts.charts.Line()
            Time = (Line
                    .add_xaxis(x_line)
                    .add_yaxis('平均调节时间',
                               Agcresult['Avet'].tolist(),
                               symbol ='circle',
                               symbol_size =5,
                               label_opts = opts.LabelOpts(is_show=False),
                               linestyle_opts = opts.LineStyleOpts(width=3))
                    .set_global_opts(
                        yaxis_opts = opts.AxisOpts(
                            max_=max(Agcresult['Avet']),
                            min_=min(Agcresult['Avet'])
                            ),
                        xaxis_opts = opts.AxisOpts(name='第k时段',name_location='middle',name_gap=25),
                        title_opts = opts.TitleOpts(title='平均调节时间/s',pos_left='center'),
                        legend_opts = opts.LegendOpts(pos_left='right')
                        )
                )
            make_snapshot(driver, Time.render(),path+'\\平均调节时间图.png')
        
        return 
    def figBat(self,path):
        BatResult = self.BatResult
        if BatResult is not None:
            x_line = BatResult.index.tolist()
            y_line = BatResult.apply(lambda x:x['DOD'],axis = 1).tolist()
            Line = pyecharts.charts.Line()
            DOD = (Line
                    .add_xaxis(x_line)
                    .add_yaxis('充放电深度',y_line,
                               label_opts = opts.LabelOpts(is_show=False),
                               linestyle_opts = opts.LineStyleOpts(width=2.5))
                    .set_global_opts(
                        title_opts = opts.TitleOpts(title='充放电深度%',pos_left='center'),
                        xaxis_opts = opts.AxisOpts(name='第k条指令',name_location='middle',name_gap=25),
                        legend_opts = opts.LegendOpts(pos_left='right')
                        )
                )
            make_snapshot(driver, DOD.render(),path+'\\DOD.png')
            y_line1 = BatResult['等效2C放电时长'].tolist()
            y_line2 = BatResult['等效2C充电时长'].tolist()
            Line = pyecharts.charts.Line()
            DengX2C = (Line
                       .add_xaxis(x_line)
                       .add_yaxis('等效2C放电时长',y_line1,
                                  label_opts = opts.LabelOpts(is_show=False))
                       .add_yaxis('等效2C充电时长',y_line2,
                                  label_opts = opts.LabelOpts(is_show=False))
                       .set_global_opts(
                           title_opts = opts.TitleOpts(title='等效2C充放电时长/s',pos_left='center'),
                           xaxis_opts = opts.AxisOpts(name='第k条指令',name_location='middle',name_gap=25),
                           legend_opts = opts.LegendOpts(pos_left='right')
                           )
                )
            make_snapshot(driver, DengX2C.render(),path+'\\等效2C时长图.png')
        return
    def figKp(self,path):
        kpresult = self.kpresult
        if kpresult is not None:
            x_line = kpresult.index.tolist()
            if len(x_line) >=5:
                m = -5
            else:
                m = 0
            Line = pyecharts.charts.Line()
            y_line = kpresult['k1'].tolist()[m:]
            K1 = (Line
                  .add_xaxis(x_line[m:])
                  .add_yaxis('k1',
                             y_line,
                             symbol = 'circle',
                             symbol_size = 7,
                             label_opts = opts.LabelOpts(is_show=False),
                             linestyle_opts = opts.LineStyleOpts(width=3))
                  .set_global_opts(
                      title_opts = opts.TitleOpts(title='k1',pos_left='center'),
                      legend_opts = opts.LegendOpts(pos_left='right'),
                      yaxis_opts = opts.AxisOpts(min_ = round(min(y_line),2),max_ = round(max(y_line),2))
                      )
                )
            make_snapshot(driver, K1.render(),path+'\\K1.png')
            Line = pyecharts.charts.Line()
            y_line = kpresult['k2'].tolist()[m:]
            K2 = (Line
                  .add_xaxis(x_line[m:])
                  .add_yaxis('k2',
                             y_line,
                             symbol = 'circle',
                             symbol_size = 7,
                             label_opts = opts.LabelOpts(is_show=False),
                             linestyle_opts = opts.LineStyleOpts(width=3))
                  .set_global_opts(
                      title_opts = opts.TitleOpts(title='k2',pos_left='center'),
                      legend_opts = opts.LegendOpts(pos_left='right'),
                      yaxis_opts = opts.AxisOpts(min_ = round(min(y_line),2),max_ = round(max(y_line),2))
                      )
                )
            make_snapshot(driver, K2.render(),path+'\\K2.png')
            Line = pyecharts.charts.Line()
            y_line = kpresult['k3'].tolist()[m:]
            K3 = (Line
                  .add_xaxis(x_line[m:])
                  .add_yaxis('k3',
                             y_line,
                             symbol = 'circle',
                             symbol_size = 7,
                             label_opts = opts.LabelOpts(is_show=False),
                             linestyle_opts = opts.LineStyleOpts(width=3))
                  .set_global_opts(
                      title_opts = opts.TitleOpts(title='k3',pos_left='center'),
                      legend_opts = opts.LegendOpts(pos_left='right'),
                      yaxis_opts = opts.AxisOpts(min_ = round(min(y_line),2),max_ = round(max(y_line),2)+0.02)
                      )
                )
            make_snapshot(driver, K3.render(),path+'\\K3.png')
            Line = pyecharts.charts.Line()
            y_line = kpresult['kp'].tolist()[m:]
            Kp = (Line
                  .add_xaxis(x_line[m:])
                  .add_yaxis('kp',
                             y_line,
                             symbol = 'rect',
                             symbol_size = 7,
                             label_opts = opts.LabelOpts(is_show=False),
                             linestyle_opts = opts.LineStyleOpts(width=3))
                  .set_global_opts(
                      title_opts = opts.TitleOpts(title='kp',pos_left='center'),
                      legend_opts = opts.LegendOpts(pos_left='right'),
                      yaxis_opts = opts.AxisOpts(min_ = round(min(y_line),2),max_ = round(max(y_line),2))
                      )
                )
            make_snapshot(driver, Kp.render(),path+'\\Kp.png')
            Line = pyecharts.charts.Line()
            y_line = kpresult['Cost'].tolist()[m:]
            Cost = (Line
                  .add_xaxis(x_line[m:])
                  .add_yaxis('成本',
                             y_line,
                             symbol = 'rect',
                             symbol_size = 7,
                             label_opts = opts.LabelOpts(is_show=False),
                             linestyle_opts = opts.LineStyleOpts(width=3))
                  .set_global_opts(
                      title_opts = opts.TitleOpts(title='成本/元',pos_left='center'),
                      legend_opts = opts.LegendOpts(pos_left='right'),
                      yaxis_opts = opts.AxisOpts(min_ = round(min(y_line),2),max_ = round(max(y_line),2))
                      )
                )
            make_snapshot(driver, Cost.render(),path+'\\成本图.png')
            Line = pyecharts.charts.Line()
            y_line = kpresult['Revenue'].tolist()[m:]
            Revenue = (Line
                  .add_xaxis(x_line[m:])
                  .add_yaxis('收益',
                             y_line,
                             symbol = 'rect',
                             symbol_size = 7,
                             label_opts = opts.LabelOpts(is_show=False),
                             linestyle_opts = opts.LineStyleOpts(width=3))
                  .set_global_opts(
                      title_opts = opts.TitleOpts(title='收益/元',pos_left='center'),
                      legend_opts = opts.LegendOpts(pos_left='right'),
                      yaxis_opts = opts.AxisOpts(min_ = round(min(y_line),2),max_ = round(max(y_line),2))
                      )
                )
            make_snapshot(driver, Revenue.render(),path+'\\收益图.png')
            Line = pyecharts.charts.Line()
            y_line = kpresult['elecFee'].tolist()[m:]
            elecFee = (Line
                  .add_xaxis(x_line[m:])
                  .add_yaxis('电费',
                             y_line,
                             symbol = 'rect',
                             symbol_size = 7,
                             label_opts = opts.LabelOpts(is_show=False),
                             linestyle_opts = opts.LineStyleOpts(width=3))
                  .set_global_opts(
                      title_opts = opts.TitleOpts(title='电费/元',pos_left='center'),
                      legend_opts = opts.LegendOpts(pos_left='right'),
                      yaxis_opts = opts.AxisOpts(min_ = round(min(y_line),2),max_ = round(max(y_line),2))
                      )
                )
            make_snapshot(driver, elecFee.render(),path+'\\电费图.png')
            Line = pyecharts.charts.Line()
            y_line1 = kpresult['充电等效次数'].apply(lambda x:-x).tolist()[m:]
            y_line2 = kpresult['放电等效次数'].tolist()[m:]
            DengXcircle = (Line
                            .add_xaxis(x_line[m:])
                            .add_yaxis('充电等效次数',
                                     y_line1,
                                     symbol = 'rect',
                                     symbol_size = 7,
                                     label_opts = opts.LabelOpts(is_show=False),
                                     linestyle_opts = opts.LineStyleOpts(width=2))
                            .add_yaxis('放电等效次数',
                                     y_line2,
                                     symbol = 'rect',
                                     symbol_size = 7,
                                     label_opts = opts.LabelOpts(is_show=False),
                                     linestyle_opts = opts.LineStyleOpts(width=3))
                            .set_global_opts(
                              title_opts = opts.TitleOpts(title='运行强度',pos_left='center'),
                              legend_opts = opts.LegendOpts(pos_left='right')
                              )
                            )
            make_snapshot(driver, DengXcircle.render(),path+'\\等效循环图.png')
        return