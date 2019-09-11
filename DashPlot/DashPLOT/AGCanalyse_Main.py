'''
Created on 2019年8月7日

@author: JesisW
'''
import scipy.io as sci
import time
import pandas as pd
import numpy as np
import sys
import os
import matplotlib.pyplot as plt
import FIGUREplot
from AGCanalyse.check_and_deal_data import Check_data,deal_data
from AGCanalyse.Base_analyse import MX,HB,GD,operation_analyse
sys.path.insert(0, r'D:\pyworkspace\Data_Get') # sys.path.append(path)也可以，只不过查询时是在最后位置，加载包的时候是按顺序查找包的
from getAPI import getStaWork
'''
    文件取数接C:取文件的时候index是不含有时间的
    path = 'C:/Users/JesisW/Desktop/XFdata.mat'
    data = sci.loadmat(path)
    M = data['XFdata']
    val = M[0,0]
    df = pd.DataFrame(val['data1203'],columns = ['Agc','Pdg','Pall'])
    接口取数接C:取接口的时候，index是含有时间的
    sta_data_date = '2019-05-16 00:00:00'
    end_data_date = '2019-05-16 22:00:00'
    sta_config=pd.read_excel('D:/pyworkspace/Data_Get/assets/sta_cl_ah_config.xlsx')
    sta_codes,sta_names=sta_config['code'],sta_config['name']
    index =      [  0,    1,    2,   5,    6,    7,   14,   15,    16,   33   ,  4]  #调频电站序号
    index_name = ['新丰','云河','准大','海丰','河源','宣化','同达','上都','平朔','鲤鱼江','兴和']
    index_loc =  ['MX' ,'GD',' MX' ,'GD', 'GD', 'HB', 'HB', 'HB', 'HB', 'GD' , 'XH']
    #  i         [  0     1     2    3     4     5     6     7     8     9   ,  10]
    i = 0 # 电站i = 0~9
    Aim_codes,Aim_names,Aim_names_Chinese = sta_codes[index[i]],sta_names[index[i]],index_name[i]
    
    A = getStaWork(sta_data_date,end_data_date,Aim_codes)
    df,df1,df2 = A.getEMSBat()
    Agc1,Agc2 = A.getEMSAgc()
    DF = pd.merge(df,Agc1,right_index=True,left_index=True,how='inner')
    time = pd.DataFrame(DF.index,columns =['time'])
    time.columns = ['time']
    data = pd.DataFrame(columns=['Agc','Pdg','Pall','Pbat'])
    data['Agc'],data['Pdg'],data['Pbat'] = DF['01Agc'],DF['01机组出力'],DF['01储能']+DF['02储能']
    data['Pall'] = data['Pdg']+data['Pbat']
'''
def makedir(file):
    folder = os.path.exists(file)
    if not folder:
        os.makedirs(file)
        print("--- new folder ---")
        print("--- OK ---")
    else:
        print("--- the folder is exist ---")

if __name__ == '__main__':
    sta_config=pd.read_excel('D:/pyworkspace/Data_Get/assets/sta_cl_ah_config.xlsx')
    index =      [  0,    1,    2,   5,    6,    7,   14,   15,   16,  33,  4]  #调频电站序号
    sta_data_date = '2019-08-22 00:00:00'
    end_data_date = '2019-08-23 00:00:00'
    dianzhan      =        5
    jizu = input('请输入机组：')
    jizu = int(jizu)
    if jizu == 1:
        Jizu = '01'
    else:
        Jizu = '02'

    if jizu not in [1,2]:
        print('错误输入机组参数，请重新输入')
        os._exit(0) # 在子程序中就是退出子程序
#     for i in sta_config['name']:
#         file = r'E:\1伪D盘\AGC运行'+'\\'+i+'\\图片'
#         makedir(file)
    # 自动获取程序
    path = r'E:\1伪D盘\AGC运行'
    K = Check_data(dianzhan)
    Aim_names,Aim_names_Chinese = K.Aim_names,K.Aim_names_Chinese
    index_loc = K.location
    data,time,Bat,Agc = K.webfile(jizu, sta_data_date, end_data_date)
    if data.empty:
        os._exit(0) # 在子程序中就是退出子程序
    Bat.to_csv(path+'\\'+Aim_names+'\\数据\\储能Data'+sta_data_date[0:10]+'-'+str(jizu)+'.csv',index = True,header=True,encoding='gbk')
    Agc.to_csv(path+'\\'+Aim_names+'\\数据\\AGCData'+sta_data_date[0:10]+'-'+str(jizu)+'.csv',index = True,header=True,encoding='gbk')
    Bat = Bat['01储能']+Bat['02储能']
    Pdg = Agc[Jizu+'机组出力']
    Agc = Agc[Jizu+'AGC']

#     人工操作
#     a = pd.read_csv(r'E:\1伪D盘\AGC运行\河北宣化电厂储能电站\数据\储能Data2019-08-22-2.csv',index_col = 0,header = 0,encoding='gbk')
#     b = pd.read_csv(r'E:\1伪D盘\AGC运行\河北宣化电厂储能电站\数据\AGCData2019-08-22-2.csv',index_col = 0,header = 0,encoding='gbk')
#     df = pd.merge(a,b,left_index=True,right_index=True,how='inner')
#     data = pd.DataFrame(columns=['Agc','Pdg','Pall','Pbat'])
#     data['Agc'],data['Pdg'],data['Pbat'] = df[Jizu+'AGC'],df[Jizu+'机组出力'],df['01储能']+df['02储能']
#     data['Pall'] = data['Pdg']+data['Pbat']
#     Bat = a['01储能']+a['02储能']
#     Agc = b[Jizu+'AGC']
#     Pdg = b[Jizu+'机组出力']
#     time = pd.to_datetime(df.index,format='%Y-%m-%d %H:%M:%S')
#     time.columns = ['time']
#     Aim_names_Chinese = '宣化'
#     index_loc = 'HB'
#     Aim_names = sta_config['name'][index[dianzhan]]

#     df = pd.read_csv(r'D:\华润海丰\Data\海丰项目26-29日AGC指令数据\29号.csv',encoding ='gbk',index_col=0,header=0)
#     df.index = df['Date']
#     time = pd.to_datetime(df['Date'],format='%Y/%m/%d %H:%M:%S')
#     time.columns = ['time']
#     data = pd.DataFrame(columns=['Agc','Pdg','Pall','Pbat'])
#     data['Agc'],data['Pdg'],data['Pall'],data['Pbat'] = df['01AGC'],df['01机组出力'],df['Pall'],df['bat']
#     Bat = df['bat']
#     Agc = df['01AGC']
#     Pdg = df['01机组出力']
#     Aim_names_Chinese = '海丰'
#     index_loc = 'GD'
#     Aim_names = sta_config['name'][index[dianzhan]]
    # 处理数据
    file = r'E:\1伪D盘\AGC运行'+'\\'+Aim_names+'\\图片'
    deal = deal_data(Aim_names_Chinese=Aim_names_Chinese,data=data,location=index_loc,Agc=Agc,Pdg=Pdg,Bat=Bat,time=time)
    Result,Result1,BatResult,ResultSingle = deal.Solv()
    # 画其他图
    fig1 = FIGUREplot.figecharts(i=dianzhan,Agcresult=Result,BatResult=BatResult)
    fig1.figAgc(file)
    fig1.figBat(file)
    # 保存数据
    ResultSingle['机组'] = jizu
    ResultSingle.index = [sta_data_date[0:10]]
    ResultSingle.index.name = 'time'
    ResultSingle.index = pd.to_datetime(ResultSingle.index,format=None)
    if os.path.exists(path+'\\'+Aim_names+'\\Kp\\data.csv'):
        ResultSingle1 = pd.read_csv(path+'\\'+Aim_names+'\\Kp\\data.csv',index_col=0,header=0,encoding='gbk')
        ResultSingle1.index = pd.to_datetime(ResultSingle1.index,format=None)
        ResultSingle1.to_csv(path+'\\'+Aim_names+'\\Kp\\备份data.csv',index = True,header=True,encoding='gbk')
#         # 手工画历史kp图
#         fig2 = FIGUREplot.figecharts(i=dianzhan,kpresult=ResultSingle1)
#         fig2.figKp(file)
        if ResultSingle.index[0] not in ResultSingle1.index:
            ResultSingle = pd.concat([ResultSingle1,ResultSingle],axis = 0)
            ResultSingle.sort_index(axis =0,inplace=True)
            ResultSingle.to_csv(path+'\\'+Aim_names+'\\Kp\\data.csv',index = True,header=True,encoding='gbk')
            ResultSingle.index.apply(lambda x: x.strftime('%Y-%m-%d'))
            # 画kp图-日更新的
            fig2 = FIGUREplot.figecharts(i=dianzhan,kpresult=ResultSingle)
            fig2.figKp(file)
        else:
            print('kp重复计算，请检查')
    else:
        ResultSingle.to_csv(path+'\\'+Aim_names+'\\Kp\\data.csv',index = True,header=True,encoding='gbk')
    Result.to_csv(path+'\\'+Aim_names+'\\AGC'+'\\'+sta_data_date[0:10]+Aim_names_Chinese+'-'+str(jizu)+'.csv',index=True,header=True,encoding='gbk')
    Result1.to_csv(path+'\\'+Aim_names+'\\机组'+'\\'+sta_data_date[0:10]+Aim_names_Chinese+'-'+str(jizu)+'.csv',index=True,header=True,encoding='gbk')
    BatResult.to_csv(path+'\\'+Aim_names+'\\储能'+'\\'+sta_data_date[0:10]+Aim_names_Chinese+'-'+str(jizu)+'.csv',index=True,header=True,encoding='gbk')