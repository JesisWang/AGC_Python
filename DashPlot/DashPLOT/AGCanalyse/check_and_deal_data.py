'''
Created on 2019年8月23日

@author: JesisW
'''
import scipy.io as sci
from AGCanalyse.Base_analyse import MX,HB,GD,operation_analyse
import os
import sys
import pandas as pd
sys.path.insert(0, r'D:\pyworkspace\Data_Get') # sys.path.append(path)也可以，只不过查询时是在最后位置，加载包的时候是按顺序查找包的
import getAPI

class Check_data():
    '''
    :检查数据，并且微处理数据
    :parm i: 电站序号
    '''
    def __init__(self,i):
        sta_config=pd.read_excel('D:/pyworkspace/Data_Get/assets/sta_cl_ah_config.xlsx')
        self.sta_codes,self.sta_names=sta_config['code'],sta_config['name']
        self.index =      [  0,    1,    2,   5,    6,    7,   14,   15,    16,   33  ,   4]  #调频电站序号
        self.index_name = ['新丰','云河','准大','海丰','河源','宣化','同达','上都','平朔','鲤鱼江','兴和']
        self.index_loc =  ['MX' ,'GD', 'MX' ,'GD', 'GD', 'HB', 'HB', 'HB', 'HB', 'GD' , 'MX']
        #       i         [  0     1     2    3     4     5     6     7     8     9      10]
        # 电站i = 0~9
        self.Aim_names,self.Aim_names_Chinese =self.sta_names[self.index[i]],self.index_name[i]
        self.Aim_codes,self.location = self.sta_codes[self.index[i]],self.index_loc[i]
        self.i = i
    
    def _Dataexist(self,start_date,end_date):
        '''
        :内部函数：用来判断电站是否存在数据，并返回存在数据的电站和序号
        '''
        Nodata =[]
        Nodata_loc =[]
        Ysdata =[]
        Ysdata_loc =[]
        for i in range(0,len(self.index)):
            Aim_codes = self.sta_codes[self.index[i]]
            sta_data_date = start_date
            end_data_date = end_date
            A = getAPI.getStaWork(sta_data_date,end_data_date,Aim_codes)
            print('开始检查电站：'+self.index_name[i])
            Agc1,Agc2 = A.getEMSexist()
            if Agc1.empty and Agc2.empty:
                Nodata.append(self.index_name[i])
                Nodata_loc.append(i)
            else:
                Ysdata.append(self.index_name[i])
                Ysdata_loc.append(i)
        return Nodata,Ysdata,Nodata_loc,Ysdata_loc
    def matfile(self,path,struct_name=None,Varname=None,column=None):
        '''
        keys:
            path:文档的路径
            struct_name:mat文件的结构体名字
            Varname:结构体下的变量名
            column:给出列的含义
        return:
            data: 读出的数据
            time: 横坐标
        '''
        if Varname is None:
            print('必须给出变量名')
            return 
        
        if struct_name is not None:
            try:
                data = sci.loadmat(path)
                M = data[struct_name]
                val = M[0,0]
                df = pd.DataFrame(val[Varname],columns = column)
                time = None
                data = pd.DataFrame(columns=['Agc','Pdg','Pall','Pbat'])
                data['Agc'],data['Pdg'],data['Pbat'] = df['AGC'],df['Pdg'],df['Pall']-df['Pdg']
                data['Pall'] = df['Pall']
            except Exception as d:
                print(d)
                print('请尝试给一个新的变量名')
                return pd.DataFrame(),None
        else:
            try:
                data = sci.loadmat(path)
                data = pd.DataFrame(data[Varname],columns=column)
                time = None
            except Exception as d:
                print(d)
                return pd.DataFrame(),None
        return data,time
    def csvfile(self,path):
        '''
        keys:
            path:文件路径
        retur:
            data:整合数据
            time:横轴
            bat:电池数据
            Agc:Agc数据
        '''
        try:
            DF = pd.read_csv(path,header =0,index_col = 0,encoding = 'gbk')
            time = pd.to_datetime(DF.index,format='%Y-%m-%d %H:%M:%S')
            time.columns = ['time']
            data = pd.DataFrame(columns=['Agc','Pdg','Pall','Pbat'])
            data['Agc'],data['Pdg'],data['Pbat'] = DF['Agc'],DF['Pdg'],DF['Pbat']
            bat = DF['Pbat']
            Agc = DF['Agc']
            if 'Pall' in DF.keys():
                data['Pall'] = DF['Pall']
            else:
                data['Pall'] = data['Pdg']+data['Pbat']
        except Exception as d:
            print(d)
            return None,None,None,None
        return data,time,bat,Agc
    def webfile(self,Jizu,start_date,end_date):
        '''
        keys:
            Jizu:机组是系统1或2
            start_date:起始时间
            end_date:结束时间
        return:
            data:AGC,电池的联合数据(时标对应的)
            time:时标，对应x轴
            bat:电池系统1和2的联合数据(时标都存在的)
            Agc:Agc数据(没做时标的联合,可能数据更大)
        '''
        if start_date is None and end_date is None:
            print('接口查询必须给定时间和电站')
            data = 0
            time = 0
        elif Jizu is None:
            print('请在运行前给出所属机组')
        else:
            sta_data_date = start_date
            end_data_date = end_date
            a,b,c,d = self._Dataexist(sta_data_date,end_data_date)
            if self.i in d:
                A = getAPI.getStaWork(sta_data_date,end_data_date,self.Aim_codes)
                bat,df1,df2 = A.getEMSBat()
                if Jizu == 1:
                    jizu = '01'
                    Agc = A.getEMSAgc(jizu)
                else:
                    jizu = '02'
                    Agc = A.getEMSAgc(jizu)
                DF = pd.merge(bat,Agc,right_index=True,left_index=True,how='inner')
                time = pd.to_datetime(DF.index,format='%Y-%m-%d %H:%M:%S')
                time.columns = ['time']
                data = pd.DataFrame(columns=['Agc','Pdg','Pall','Pbat'])
                data['Agc'],data['Pdg'],data['Pbat'] = DF[jizu+'AGC'],DF[jizu+'机组出力'],DF['01储能']+DF['02储能']
                data['Pall'] = data['Pdg']+data['Pbat']
                data.index = pd.to_datetime(data.index,format=None)
                bat.index = pd.to_datetime(bat.index,format=None)
                Agc.index = pd.to_datetime(Agc.index,format=None)
            elif self.i in c:
                print(self.Aim_names_Chinese+'无数据，请尝试换一个电站')
                print('经查询：电站'+str(a)+'无数据 \n'+'电站'+str(b)+'有数据')
                data = pd.DataFrame()
                bat = pd.DataFrame()
                Agc = pd.DataFrame()
                time = 0
        return data,time,bat,Agc

class deal_data():
    '''
    :数据分析外部接口
    :param Aim_names_Chinese:电站中文名简称
    :param data:分析数据，通常包括AGC数据列，时间列，联合出力列
    :param location:电站所在区域：华北，蒙西及广东
    :param Agc:Agc数据列，可用来单独分析
    :param Pdg:机组数据列，可用来单独分析
    :param Bat:储能数据列，可用来单独分析
    :param time:时间类，可不添加，若存在，最好加入
    
    :return 各项分析结果：kp值，机组出力分析，储能出力分析，AGC指令情况分析，收益分析，成本分析
    '''
    def __init__(self,Aim_names_Chinese,data,location,Agc,Pdg,Bat,time=None):
        self.Chinese_name = Aim_names_Chinese
        self.data = data
        self.location = location
        self.Agc = Agc
        self.Pdg = Pdg
        self.Bat = Bat
        self.Agctime = pd.to_datetime(Agc.index,format='%Y-%m-%d %H:%M:%S')
        self.Agctime.columns =['time']
        self.time = time
    
    def Solv(self,detAgc = 2,initial_SOC = 50,scanrate =1):
        if self.location in 'MX':
            C = MX(stationname =  self.Chinese_name,Agc = self.data['Agc'],Pdg = self.data['Pdg'],Pall=self.data['Pall'],Pbat=self.data['Pbat'],time=self.time)
            A = operation_analyse(stationname =  self.Chinese_name,Agc = self.Agc,Pdg = self.Pdg,time = self.Agctime)
            ScanR = 1
            k1,k2,k3,kp,D,Revenue,Result_Agc = C.Kp_Revenue(ScanR =ScanR)
        elif self.location in 'GD':
            C = GD(stationname = self.Chinese_name,Agc = self.data['Agc'],Pdg =self.data['Pdg'],Pall=self.data['Pall'],Pbat=self.data['Pbat'],time=self.time)
            A = operation_analyse(stationname =  self.Chinese_name,Agc = self.Agc,Pdg = self.Pdg,time = self.Agctime)
            ScanR = 1
#             Conclusion = C.Contribution()
            k1,k2,k3,kp,D,Revenue,Result_Agc = C.Kp_Revenue(ScanR =ScanR)
        elif self.location in 'HB':
            C = HB(stationname = self.Chinese_name,Agc = self.data['Agc'],Pdg =self.data['Pdg'],Pall=self.data['Pall'],Pbat=self.data['Pbat'],time=self.time)
            A = operation_analyse(stationname =  self.Chinese_name,Agc = self.Agc,Pdg = self.Pdg,time = self.Agctime)
            ScanR = 5
            k1,k2,k3,kp,D,Revenue,Result_Agc = C.Kp_Revenue(ScanR =ScanR)
        BatResult,Cost,elecFee,Eqv_cycminus,Eqv_cycplus = C.BATstrength(initial_SOC = 0, detAgc =detAgc, scanrate =scanrate)
        Result = A.AGCstrength(detAgc = detAgc)
        Result1,Op1,Op2,Op3,Op4,S,M,P = A.PDGstrength(detAgc= detAgc)
        ResultSingle = pd.DataFrame(columns=['k1','k2','k3','kp','D','Revenue','Cost','elecFee','充电等效次数','放电等效次数','反调','不动','缓调','瞬间完成','有效','总次数','比例'])
        ResultSingle.loc[0] =k1,k2,k3,kp,D,Revenue,Cost,elecFee,Eqv_cycminus,Eqv_cycplus,Op1,Op2,Op3,Op4,S,M,P
#         print(k1,k2,k3,kp,D)
#         return Result,Result1,BatResult,ResultSingle
        return kp,k1,k2,k3,D,Result_Agc
class data_flow(Check_data):
    
    def __init__(self,m=True):
        f = m