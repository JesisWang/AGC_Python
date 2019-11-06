'''
Created on 2019年10月8日
AGC_Pdgdata_man_made
@author: JesisW
'''
import pandas as pd
import numpy as np

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

class AGC_control_GD():
    """
    :用来生成AGC控制策略中储能的输出
     
    :param Agc:1s每点的连续AGC数据 
    :param Pdg:1s每点的连续机组数据 
    :param Pdg_e:机组额定功率
    :param Pbat_Pe:储能额定功率
    :param Capacity:储能容量 
    :param Area:所在地区
    :param V:储能期望速率
     
    :return Pbat:储能输出功率
    """
    Pbat = []
    def __init__(self,Agc,Pdg,Pdg_e,Pbat_Pe,Capacity,Area,V):
        self.Agc = Agc
        self.Pdg = Pdg
        self.Pe = Pdg_e
        self.Pbat_v = V
        self.Pbat_Pe = Pbat_Pe
        self.Pbat_Capacity = Capacity
        self.V_t_period = 4 #测速时间
        self.V_dead_zone = min(5,self.Pe*0.005)
        if Area == '广东':
            self.response_dead = min([self.Pe*0.005,5])
            self.adjust_dead = min([self.Pe*0.005,5])
            self.Vn = self.Pe*0.01903
            self.tn = 300
            self.detPn = self.Pe*0.015
        return
     
    def Response(self,Pdg,Response_Aim,flag):
        if flag>0:
            Aim = max(Pdg,Response_Aim)
            Bat = min(self.Pbat[-1]+self.V,Aim-Pdg)
        else:
            Aim = min(Pdg,Response_Aim)
            Bat = max(self.Pbat[-1]-self.V,Aim-Pdg)
        Bat = min(Bat,self.discharge)
        Bat = max(Bat,self.charge)
        self.Pbat.append(Bat)
        return
         
    def TestV(self,start,end,Pdg,flag,lastAgc):
        if (end-start)*flag<=0:
            if flag>0:
                Bat = self.Pbat[-1]+self.V
                Bat = min(Bat,lastAgc-Pdg)
            else:
                Bat = self.Pbat[-1]-self.V
                Bat = max(Bat,lastAgc-Pdg)
            self.Pbat.append(Bat)
            return
        else:
            if flag>0:
                Bat = self.Pbat[-1]+self.V
                Bat = min(Bat,end+1-Pdg)
            else:
                Bat = self.Pbat[-1]-self.V
                Bat = max(Bat,end-1-Pdg)
            self.Pbat.append(Bat)
            
        return
    
    def D_improve(self,flag):
        if flag>0:
            Bat = self.Pbat[-1]+self.V
            Bat = min(Bat,self.discharge)
        else:
            Bat = self.Pbat[-1]-self.V
            Bat = max(Bat,self.charge)
        self.Pbat.append(Bat)
        return
    
    def Ajust(self,lastAgc,Pdg,flag):
        Aim = lastAgc-Pdg
        if abs(Aim-self.Pbat[-1])>self.V:
            if Aim<self.Pbat[-1]:
                Bat = self.Pbat[-1]-self.V
            else:
                Bat = self.Pbat[-1]+self.V
        else:
            Bat = Aim
        Bat = min(Bat,self.discharge)
        Bat = max(Bat,self.charge)    
        self.Pbat.append(Bat)
        return
    
    def Reback(self,Pdg,Agc,Maintain_Value):
        '''含有维护的程序'''
        if self.SOC<40-Maintain_Value:
            if Pdg>Agc:
                '''有提供充电能力时维护'''
                if self.Pbat[-1]>0:
                    prob = min(Pdg-Agc,self.Pbat_Pe/20)
                    Bat = min(self.V,self.Pbat[-1]+prob)
                    Bat = self.Pbat[-1]-Bat
                else:
                    prob = min(Pdg-Agc,self.Pbat_Pe/20)
                    Bat = min(self.V,-prob-self.Pbat[-1])
                    Bat = self.Pbat[-1]+Bat
            else:
                '''否则不维护soc'''
                if self.Pbat[-1]>0:
                    Bat = min(self.V,self.Pbat[-1]-0)
                    Bat = self.Pbat[-1]-Bat
                else:
                    Bat = min(self.V,0-self.Pbat[-1])
                    Bat = self.Pbat[-1]+Bat
        elif self.SOC>60+Maintain_Value:
            if Pdg<Agc:
                if self.Pbat[-1]>0:
                    prob = min(Agc-Pdg,self.Pbat_Pe/20)
                    Bat = min(self.V,self.Pbat[-1]-prob)
                    Bat = self.Pbat[-1]-Bat
                else:
                    prob = min(Agc-Pdg,self.Pbat_Pe/20)
                    Bat = min(self.V,prob-self.Pbat[-1])
                    Bat = self.Pbat[-1]+Bat
            else:
                if self.Pbat[-1]>0:
                    Bat = min(self.V,self.Pbat[-1]-0)
                    Bat = self.Pbat[-1]-Bat
                else:
                    Bat = min(self.V,0-self.Pbat[-1])
                    Bat = self.Pbat[-1]+Bat
        else:
            if self.Pbat[-1]>0:
                Bat = min(self.V,self.Pbat[-1]-0)
                Bat = self.Pbat[-1]-Bat
            else:
                Bat = min(self.V,0-self.Pbat[-1])
                Bat = self.Pbat[-1]+Bat
        self.Pbat.append(Bat)
        return
    
    def Pbat_data_creat(self,V_mode=1,Maintain_mode=1,pull_D_mode=1):
        """
        :param V_mode:速率选择模式,1-固定速率,2-变速率
        :param Maintain_mode:维护选择模式,0-不含有维护soc,1-含有维护soc
        :param pull_D_mode:提升D选择模式,0-不提升D,1-提升D
        """
        Length = len(self.Agc)
        test_v_response = max(self.Pe*0.01,5)
        self.V_mode = V_mode
        '''
        :初始化
        '''
        lastAgc = self.Agc[0]
        Pdg0 = self.Pdg[0]
        if lastAgc>Pdg0:
            flag = 1
        else:
            flag = -1
        Response_Aim = self.response_dead*flag+Pdg0
        test_v_start = Pdg0+test_v_response*flag
        test_v_end = 0.7*lastAgc+0.3*Pdg0
        Ajustment_Aim = -self.adjust_dead*flag+lastAgc
        if Maintain_mode == 0:
            Maintain_Value = 40 # 不维护soc
        elif Maintain_mode == 1:
            Maintain_Value = 0 # 维护soc
            
        if pull_D_mode == 0:
            constant_D = 86400
        elif pull_D_mode == 1:
            constant_D = 0
        
        if self.V_mode == 1:
            self.V = self.Pbat_v # 固定速率方法
        else:
            if (test_v_end-test_v_start)*flag<=self.V_dead_zone:
                V_actual = 0
            else:
                V_actual = (test_v_end-test_v_start)*flag/self.V_t_period
            self.V = max(V_actual,self.Pbat_v)# 变速率方法
            self.V = min(self.V,10)
        n = 0 # 用来计时60s
        m = 0 # 调节时间40s
        c = 0 # 用来计时4s
        delay_time = 1 # 新来指令后的迟滞时间计时
        Response_state = 0
        V_state = 0
        Ajust_state = 0
        SOC_state = 0 # 是否响应D值
        Finsh_state = 0 # 是否到达调节死区
        if flag>0:
            if test_v_end<Response_Aim or test_v_end<test_v_start:
                V_state = 1
            if Ajustment_Aim<Response_Aim:
                Response_state = 1
                V_state = 1
                Ajust_state = 0
            if Ajustment_Aim<test_v_end:
                V_state = 1
        self.Pbat.append(0)
        self.charge = -self.Pbat_Pe
        self.discharge = self.Pbat_Pe
        self.SOC = 41.7
        '''开始循环'''
        for i in range(1,Length):
            if i == 653:
                print(i)
#             print(i,len(self.Pbat))
            lastPall = self.Pdg[i-1]+self.Pbat[i-1]
            if abs(self.Agc[i]-lastAgc)>5:
                lastAgc = self.Agc[i]
                if lastAgc>lastPall:
                    flag = 1
                else:
                    flag = -1
                Response_Aim = self.response_dead*flag+lastPall
                test_v_start = lastPall+test_v_response*flag
                test_v_end = 0.7*lastAgc+0.3*lastPall
                Ajustment_Aim = -self.adjust_dead*flag+lastAgc
                Response_state = 0
                V_state = 0
                Ajust_state = 0
                SOC_state = 0 # 是否响应D值
                Finsh_state = 0 # 是否到达调节死区
                if flag>0:
                    if test_v_end<Response_Aim or test_v_end<test_v_start:
                        V_state = 1
                    if Ajustment_Aim<Response_Aim:
                        Response_state = 1
                        V_state = 1
                        Ajust_state = 0
                    if Ajustment_Aim<test_v_end:
                        V_state = 1
                if flag<0:
                    if test_v_end>Response_Aim or test_v_end>test_v_start:
                        V_state = 1
                    if Ajustment_Aim>Response_Aim:
                        Response_state = 1
                        V_state = 1
                        Ajust_state = 0
                    if Ajustment_Aim>test_v_end:
                        V_state = 1
                if self.V_mode == 1:
                    self.V = self.Pbat_v # 固定速率方法
                elif self.V_mode == 2:
                    if (test_v_end-test_v_start)*flag<=0:
                        V_actual = 0
                    else:
                        V_actual = (test_v_end-test_v_start)*flag/self.V_t_period
                    self.V = max(V_actual,self.Pbat_v)# 变速率方法
                n = 0 # 用来计时60s
                m = 0 # 调节时间40s
                c = 0 # 用来计时4s
                delay_time = 1 # 新来指令后的迟滞时间计时
            if delay_time < 4:
                '''迟滞3s'''
                self.Pbat.append(self.Pbat[-1])
                delay_time += 1
            else:
                if flag>0:
                    '''进行响应死区的调节'''
                    if Response_state == 0:#lastPall<=Response_Aim and
                        self.Response(self.Pdg[i],Response_Aim,flag)
                    elif V_state == 0:#Response_Aim<lastPall<=test_v_end and
                        '''进行速度调节或D值调节'''
                        n += 1
                        if test_v_end-lastPall>self.discharge-self.Pbat[-1]:
                            '''若储能自身无法完成测速'''
                            if n <= 60+constant_D:
                                '''若机组始终无法满足条件，60s内采用维持出死区状态处理'''
                                self.Response(self.Pdg[i],Response_Aim,flag)
                            else:
                                '''60s后，若soc合理，则进行D值获取，否则仍旧维持原状'''
                                if SOC_state == 0:
                                    if self.SOC>30:
                                        SOC_state = 1
                                if SOC_state>0:
                                    self.D_improve(flag)
                                else:
                                    self.Response(self.Pdg[i], Response_Aim, flag)
                        else:
                            '''储能自身可完成速率区间'''
                            self.TestV(test_v_start, test_v_end, self.Pdg[i], flag,lastAgc)
                        if (self.Pdg[i]+self.Pbat[-1]-test_v_end)*flag>=0:
                            V_state = 1
                        if i == len(self.Pbat)+2:
                            self.Pbat.pop(-2)
                    elif Ajust_state ==0:#lastPall>test_v_end and 
                        '''进行调节死区响应'''
                        if Finsh_state == 0:
                            if lastAgc-self.response_dead<=lastPall<=lastAgc+self.response_dead:
                                Finsh_state = 1
                        if Finsh_state >0:
                            m += 1
                        if m<=60:
                            '''进入调节死区维持60s'''
                            self.Ajust(self.Agc[i],self.Pdg[i],flag)
                        else:
                            '''然后退出,进入维护SOC状态'''
                            self.Reback(self.Pdg[i],self.Agc[i],Maintain_Value)
                    if lastPall >= Response_Aim:
                        c += 1
                        if c>=4:
                            Response_state = 1
                if flag<0:
                    '''进行响应死区的调节'''
                    if Response_state == 0:
                        self.Response(self.Pdg[i],Response_Aim,flag)
                    elif V_state == 0:
                        '''进行速度调节或D值调节'''
                        n += 1
                        if test_v_end-lastPall<self.charge-self.Pbat[-1]:
                            if n <= 60+constant_D:
                                self.Response(self.Pdg[i],Response_Aim,flag)
                            else:
                                if SOC_state == 0:
                                    if self.SOC<70:
                                        SOC_state = 1
                                if SOC_state>0:
                                    self.D_improve(flag)
                                else:
                                    self.Response(self.Pdg[i], Response_Aim, flag)
                        else:
                            self.TestV(test_v_start, test_v_end, self.Pdg[i], flag,lastAgc)
                        if (self.Pdg[i]+self.Pbat[-1]-test_v_end)*flag>=0:
                            V_state = 1
                        if i == len(self.Pbat)+2:
                            self.Pbat.pop(-2)
                    elif Ajust_state ==0:
                        '''进行调节死区响应'''
                        if Finsh_state == 0:
                            if lastAgc-self.response_dead<=lastPall<=lastAgc+self.response_dead:
                                Finsh_state = 1
                        if Finsh_state>0:
                            m += 1
                        if m<=40:
                            self.Ajust(self.Agc[i],self.Pdg[i],flag)
                        else:
                            self.Reback(self.Pdg[i],self.Agc[i],Maintain_Value)
                    if lastPall <= Response_Aim:
                        c += 1
                        if c>=4:
                            Response_state = 1
                self.SOC = self.SOC - self.Pbat[-1]*1/3600/self.Pbat_Capacity*100
                print(self.SOC)
                if self.SOC>95:
                    self.charge = 0
                    self.discharge = self.Pbat_Pe
                elif self.SOC<5:
                    self.discharge = 0
                    self.charge = -self.Pbat_Pe
                else:
                    self.discharge = self.Pbat_Pe
                    self.charge = -self.Pbat_Pe
                delay_time += 1
        return      
     
def main():
    file = r'E:\1伪D盘\EMS仿真平台\仿真测试数据1'
    df = pd.read_excel(file+'\\'+'组织测试数据1.xlsx',encoding='gbk',header=0)
    AGC = df['2#AGC指令']
    f = Pdg_data(AGC,1000,delay_zone=60,dead_zone=0.005,v_proportion=0.015,precision=0.02)
    f.Simulation()
    Pdg = pd.DataFrame(f.Pdg,columns=['Pdg'])
    Pdg.to_csv(file+'\\'+'组织测试数据1-机组部分-15MW-60s.csv',encoding='gbk',index=False,header=True)
    return

def main2():
    file = r'E:\1伪D盘\EMS仿真平台\仿真测试数据1'
    df = pd.read_excel(file+'\\'+'组织测试数据1.xlsx',encoding='gbk',header=0)
    AGC = df['2#AGC指令']
    PDG = df['2#机组出力']
    f = AGC_control_GD(AGC,PDG,1000,30,15,'广东',3)
    f.Pbat_data_creat()
    Pbat = f.Pbat
    Pbat = pd.DataFrame(Pbat);Pbat.columns = ['储能出力']
    Pbat.to_csv(file+'\\'+'组织测试数据1-储能部分.csv',encoding='gbk',index=False,header=True)
    return
if __name__ == '__main__':
    main2()