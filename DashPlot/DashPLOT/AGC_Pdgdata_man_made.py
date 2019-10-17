'''
Created on 2019年10月8日
AGC_Pdgdata_man_made
@author: JesisW
'''
import pandas as pd
import numpy as np
from enum import Flag

class Pdg_data():
    """
    :机组功率生成
    
    :param Agc_data:AGC数据
    :Param Pdg_e:机组额定功率(1000,300,330)
    :Param delay_zone:延迟时间(10s,20s,30s,40s...)
    :Param dead_zone:死区比例(广东0.5%,其他1%)
    :Param v_proportion:速度相对比例(1.5%)
    :Param precision:机组的正常波动比例(0.8%)
    
    :return Pdg:返回的机组功率
    """
    Pdg = []
    
    def __init__(self,Agc_data,Pdg_e,delay_zone,dead_zone,v_proportion,precision):
        self.Agc = Agc_data
        self.Agc.index = np.arange(len(self.Agc))
        self.Pe = Pdg_e
        self.Dead_zone = self.Pe*dead_zone
        self.V = self.Pe*v_proportion/60
        self.delay_zone = delay_zone
        self.precision = precision
    
    def delay(self,last_Agc,flag,det_T):
        """
        :用于生成延迟部分数据
        
        :param last_Agc:上一次的AGC指令值
        :param flag:调节方向
        :param det_T:整条指令持续时间
        
        :return det_T:剩余调节时间
        """
        N = 1
        delay_time = np.random.randint(low = self.delay_zone/2,high = 2*self.delay_zone)
        Pdg0 = self.Pdg[-1]
        delay_bound = Pdg0+flag*self.Dead_zone
        if flag>0:
            delay_bound = min(delay_bound,last_Agc-self.Dead_zone)
        else:
            delay_bound = max(delay_bound,last_Agc+self.Dead_zone)
        if det_T <=0:
            return det_T
        
        while abs(self.Pdg[-1]-Pdg0)<self.Dead_zone:
            if (self.Pdg[-1]-delay_bound)*flag>=0:
                break
            
            if det_T<=0:
                break
            
            if N < delay_time:
                detPdg = self.Pdg[-1]+np.random.randn(1)*np.sqrt(self.precision)
                self.Pdg.append(detPdg[0])
                N += 1
                det_T -= 1
            else:
                detPdg = self.Pdg[-1]+self.V*flag+np.random.randn(1)*np.sqrt(self.precision)
                self.Pdg.append(detPdg[0])
                N += 1
                det_T -= 1
            
        return det_T
        
    def Speed(self,flag,Agc_aim,det_T):
        """
        :升降负荷部分的机组功率
        
        :param flag:调节方向
        :param Agc_aim:本次AGC调节的目标值
        
        :return det_T:剩余调节时间
        """
        Pdg_v_aim = Agc_aim-self.Dead_zone*flag
        T = self.Dead_zone/self.V
        T = min(abs((Agc_aim-self.Pdg[-1])/self.V),T)
        N = 0
        m = True
        if det_T<=0:
            return det_T
        
        while m:
            detPdg = self.Pdg[-1]+self.V*flag+np.random.randn(1)*np.sqrt(self.precision)
            if flag*(self.Pdg[-1]-Pdg_v_aim)<0:
                self.Pdg.append(detPdg[0])
                det_T -= 1
            else:
                if N<T:
                    self.Pdg.append(detPdg[0])
                    N += 1
                    det_T -= 1
                else:
                    m = False
            if det_T<=0:
                return det_T
        return det_T
    
    def Stabilitiy(self,Agc_aim,det_T):
        """
        :调节精度的模拟
        
        :param Agc_aim:上次Agc的调节目标
        :param det_T:剩余调节时间
        
        :return det_T:剩余调节时间
        """
        m = True
        while m:
            if det_T<=0:
                m = False
                return det_T
            else:
                detPdg = Agc_aim+np.random.randn(1)*np.sqrt(self.precision)
                self.Pdg.append(detPdg[0])
                det_T -= 1
        return det_T
    
    def Over_adjust(self,flag,Merge_flag,Stage2_flag,det_T):
        """
        :只有当折返调节时才设定有过调且当机组完成时也不过调
        
        :param flag:本次调节方向
        :param Merge_flag:是否合并判断
        :param det_T:剩余调节时间
        
        :return det_T:剩余调节时间        
        """
        N = 1
        Over_time = np.random.randint(low = self.delay_zone/3,high = self.delay_zone/2)
        if Merge_flag>0 or Stage2_flag>0:
            return det_T
        if det_T<=0:
            return det_T
        
        while N <= Over_time:
            detPdg = self.Pdg[-1]-self.V*flag+np.random.randn(1)*np.sqrt(self.precision)
            self.Pdg.append(detPdg[0])
            N += 1
            det_T -= 1
            if det_T<=0:
                break
        return det_T
    
    def Simulation(self):
        """
        :仿真主程序
        """
        error_zone = self.Pe*0.002
        last_Agc = self.Agc.iloc[0]
        last_time = 0
        self.Pdg.append(self.Agc.iloc[0]-1)
        Stage2_flag = 1
        if self.Pdg[-1]<=last_Agc:
            flag = 1
        else:
            flag = -1
        for i in range(1,len(self.Agc)):
            if abs(self.Agc.iloc[i]-last_Agc)>error_zone:
                if self.Pdg[-1]<=last_Agc:
                    if flag == 1:
                        Merge_flag = 1
                    else:
                        Merge_flag = -1
                    flag = 1
                else:
                    if flag == -1:
                        Merge_flag = 1
                    else:
                        Merge_flag = -1
                    flag = -1
                if Stage2_flag >0 or Merge_flag<0:
                    # 要么完成了,要么折返了,都从延迟开始
                    det_T = i - last_time
                    det_T = self.Over_adjust(flag, Merge_flag, Stage2_flag, det_T)
                    Stage2_flag = 0
                    det_T = self.delay(last_Agc, flag, det_T)
                    det_T = self.Speed(flag, last_Agc,det_T)
                    if det_T>0:
                        Stage2_flag = 1 #调速是否完成
                    det_T = self.Stabilitiy(last_Agc,det_T)
                else:
                    # 上条指令没有完成且合并了,不存在延迟
                    if np.random.rand()>0.8:
                        # 80%的概率在合并时延迟稳定一会
                        det_T = self.delay(last_Agc, flag, det_T)
                    det_T = i - last_time
                    det_T = self.Speed(flag, last_Agc,det_T)
                    if det_T>0:
                        Stage2_flag = 1
                    det_T = self.Stabilitiy(last_Agc,det_T)
                last_time = i
                last_Agc = self.Agc.iloc[i]
            if i == len(self.Agc)-1:
                # 最后一条时没有Agc的比较大小
                det_T = i - last_time
                if self.Pdg[-1]<=last_Agc:
                    flag = 1
                else:
                    flag = -1
                det_T = self.delay(last_Agc, flag, det_T)
                det_T = self.Speed(flag, last_Agc,det_T)
                det_T = self.Stabilitiy(last_Agc,det_T)
        return

def main():
    file = r'E:\1伪D盘\EMS仿真平台\仿真测试数据1'
    df = pd.read_excel(file+'\\'+'组织测试数据1.xlsx',encoding='gbk',header=0)
    AGC = df['2#AGC指令']
    f = Pdg_data(AGC,1000,30,0.005,0.015,0.02)
    f.Simulation()
    Pdg = pd.DataFrame(f.Pdg,columns=['Pdg'])
    Pdg.to_csv(file+'\\'+'组织测试数据1-机组部分.csv',encoding='gbk',index=False,header=True)
    return
if __name__ == '__main__':
    main()