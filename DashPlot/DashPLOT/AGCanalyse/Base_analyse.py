'''
Created on 2019年7月29日

@author: JesisW
'''
import pandas as pd
import numpy as np
import time
import math

class operation_analyse:
    '''
    :运行得到AGC相关分析:
    :电站名称：新丰，云河，海丰，河源，鲤鱼江，恒运，宣化，准大，兴和，上都，平朔，同达
    :类下变量说明：
    Agc:Agc数据
    Pdg:机组功率数据
    Pbat:储能电站功率数据
    Pall:联合功率数据
    df:四数据的数据表
    Length:时间长度
    Pe:机组额定功率，MW
    BatPe:储能额定功率，MW
    deadzone1:响应死区大小，MW
    deadzone2:调节死区大小，MW
    Vn:调节速率大小，MW/min
    tn:标准响应时间，s
    detPn:标准调节精度，MW
    __init__的初始化参数有：
        stationname:电站名称(必须给出)
        Agc:AGC数据列(最少一日数据)
        Pdg:机组数据列(最少一日数据)
        Pbat:储能数据类(最少一日数据)
        Pall:联合数据列(最少一日数据)
        Dead1:响应死区比例系数
        Dead2:调节死区比例系数
        p:机组额定功率
        v:标准调节速率比例系数
        t:标准响应时间
        DETPN:标准调节稳定比例系数
    AGCstrength:求解AGC运行强度分析
    BATstrength:求解储能电站运行强度
    PDGstrength:求解机组运行分析,其中result包含每条指令AGC
    '''
    def __init__(self,stationname,Agc=None,Pdg=None,Pbat=None,Pall=None,Dead1=None,Dead2=None,p=None,v=None,t=None,DETPN=None,time=None):
        '''
        Constructor
        stationname:电站名称(必须给出)
        Agc:AGC数据列(最少一日数据)
        Pdg:机组数据列(最少一日数据)
        Pbat:储能数据类(最少一日数据)
        Pall:联合数据列(最少一日数据)
        Dead1:响应死区比例系数
        Dead2:调节死区比例系数
        p:机组额定功率
        v:标准调节速率比例系数
        t:标准响应时间
        DETPN:标准调节稳定比例系数
        '''
        self.stationname = stationname
        Stationname = ['新丰','云河','海丰','河源','鲤鱼江','恒运','宣化','准大','兴和','上都','平朔','同达']
        Area =        ['蒙西','广东','广东','广东','广东' ,'广东','华北','蒙西','蒙西','华北','华北','华北']
        AREA = dict(zip(Stationname,Area))
        Pe = [300,330,1000,600,300,300,330,300,300,600,300,300] # 机组额定功率
        Pe = dict(zip(Stationname,Pe))
        self.Pe = Pe[stationname]
        BatPe = [9,9,30,18,12,15,9,9,9,18,9,9] # 电池的额定功率，固定值，写死
        BatPe = dict(zip(Stationname,BatPe))
        self.BatPe = BatPe[stationname]
        if AREA[stationname] == '蒙西':
            self.deadzone1 = self.Pe*0.012
            self.deadzone2 = self.Pe*0.01
            self.Vn = self.Pe*0.015
            self.tn = 60
            self.detPn = self.Pe*0.008
        elif AREA[stationname] == '广东':
            self.deadzone1 = min([self.Pe*0.005,5])
            self.deadzone2 = min([self.Pe*0.005,5])
            self.Vn = self.Pe*0.01751#0.01903
            self.tn = 300
            self.detPn = self.Pe*0.015
        elif AREA[stationname] == '华北':
            self.deadzone1 = self.Pe*0.01
            self.deadzone2 = self.Pe*0.01
            self.Vn = self.Pe*0.015
            self.tn = 60
            self.detPn = self.Pe*0.01
        if p is not None:
            self.Pe = p
        if Dead1 is not None:
            self.deadzone1 = self.Pe*Dead1
        if Dead2 is not None:
            self.deadzone2 = self.Pe*Dead2
        if v is not None:
            self.Vn = self.Pe*v
        if t is not None:
            self.tn = t
        if DETPN is not None:
            self.detPn = self.Pe*DETPN
        if time is not None:
            self.time = pd.to_datetime(time,format='%Y-%m-%d %H:%M:%S')
        else:
            self.time = pd.date_range(start='00:00:00',periods=len(time),freq='1S')

        self.df = pd.DataFrame(columns= ['Agc','Pbat','Pdg','Pall'])
        if not Agc is None:
            self.df['Agc'] = Agc
            self.Agc = Agc
        
        if not Pdg is None:
            self.df['Pdg'] = Pdg
            self.Pdg = Pdg
        elif (Pbat is not None) and (Pall is not None):
            self.df['Pdg'] = Pall - Pbat
            self.Pdg = Pall - Pbat
        
        if not Pbat is None:
            self.df['Pbat'] = Pbat
            self.Pbat = Pbat
        elif (Pall is not None) and (Pdg is not None):
            self.df['Pbat'] = Pall - Pdg
            self.Pbat = Pall - Pdg
        
        if not Pall is None:
            self.df['Pall'] = Pall
            self.Pall = Pall
        elif (Pbat is not None) and (Pdg is not None):
            self.df['Pall'] = Pbat + Pdg
            self.Pall = Pbat + Pdg

    def AGCstrength(self,detAgc = 2):
        '''
        :输入参数：
        detAgc : 区分AGC之间的阈值
        :输出参数:
        Result的数据表:(字段含义)
        'Max':max value during the 15 minutes
        'Min':min value during the 15 minutes
        'Ave':average value during the 15minutes
        'Beg':initial value during the 15minutes
        'End':final value during the 15 minutes
        'SaD':max change in the same dirction
        'SaDt':the time t for SaD
        'Ret':reentry change
        'Num':the number of AGC order
        'Avet':the average time of AGC during the 15 minutes
        '''
        Result = pd.DataFrame(columns=['Max','Min','Ave','Beg','End','SaD','SaDt','Ret','Num','Avet'])
        Record = pd.DataFrame(columns=['Agc','i0','iend','flag'])
        AGC = self.Agc
        L1 = len(AGC)
        time = self.time
        AGC.index = time
        starttime = time[0]
        endtime = time[-1]
        Time = pd.date_range(start = starttime,end = endtime,freq = '15T')# 分钟单位是T
        Time.insert(len(Time),Time[-1]+1)
        if  L1< 900:
            print('请检查数据，保证数据最少为900条，15分钟(每秒记录)的数据')
            return
        else :
            Length = len(Time)
            for i in range(Length):
                if i <= Length-2:
                    k = time[(time>=Time[i]) & (time<Time[i+1])]
                else:
                    k = time[(time>=Time[i])]
                if k.empty:
                    Result.loc[i] = 0
                    continue
                N = i;
                Result.loc[N] = 0
                Result.loc[N,0:3] = AGC[k].max(),AGC[k].min(),AGC[k].mean()
                Record = pd.DataFrame(columns=['Agc','i0','iend','flag'])
                ctl = 0
                Record.loc[ctl,0:2] = AGC[k[0]],k[0]
                Pm = 0
                Tm = 0
                Plus = 0
                Tplus = 0
                Minus = 0
                Tminus = 0
                for j in k:
                    if abs(AGC.loc[j]-Record.ix[ctl,'Agc'])>detAgc:
                        Record.ix[ctl,'iend'] = j
                        ctl = ctl+1
                        Record.loc[ctl,'Agc'] = AGC.loc[j]
                        Record.ix[ctl,'i0'] = j
                Record.ix[ctl,'iend'] = j
                
                for j in np.arange(1,ctl+1):
                    if Record.ix[j,'Agc'] > Record.ix[j-1,'Agc']:
                        Plus = Plus+ Record.ix[j,'Agc']-Record.ix[j-1,'Agc']
                        if Tplus == 0:
                            Tplus = (Record.ix[j-1,'iend']-Record.ix[j-1,'i0']).total_seconds()
                        Tplus = Tplus+ (Record.ix[j,'iend']-Record.ix[j,'i0']).total_seconds()
                        Record.ix[j,'flag'] = 1
                        Minus = 0
                        Tminus = 0
                    else :
                        Plus = 0
                        Tplus = 0
                        Record.ix[j,'flag'] = -1
                        Minus =Minus+ Record.ix[j,'Agc'] - Record.ix[j-1,'Agc']
                        if Tminus == 0:
                            Tminus = (Record.ix[j-1,'iend'] - Record.ix[j-1,'i0']).total_seconds()
                        Tminus =Tminus + (Record.ix[j,'iend'] - Record.ix[j,'i0']).total_seconds()
                    
                    if Plus > -Minus:
                        if Plus >Pm:
                            Tm = Tplus
                            Pm = Plus
                    else :
                        if -Minus>Pm:
                            Tm = Tminus
                            Pm = -Minus
                if ctl == 0:
                    Pm = 0
                    Tm = 0
                
                if Pm>=0:
                    Result.ix[N,5] = Pm
                    Result.ix[N,6] = Tm

                Turnb = np.multiply(Record.ix[0:len(Record)-2,'flag'],Record.ix[1:,'flag'])
                Result.ix[N,3] = Record.ix[0,'Agc']
                Result.ix[N,4] = Record.ix[ctl,'Agc']
                Result.ix[N,7] = abs(sum(Turnb[Turnb<0]))
                Result.ix[N,8] = ctl
                if len(Record) == 1:
                    # 只有一条（15min都是1条）
                    Tempdata = Record.ix[0:len(Record)-1,'iend'] - Record.ix[0:len(Record)-1,'i0']
                else:
                    # 存在多条时不计最后一条（因为没有完成）
                    Tempdata = Record.ix[0:len(Record)-2,'iend'] - Record.ix[0:len(Record)-2,'i0']
                Result.ix[N,9] = Tempdata.mean().total_seconds()
        return Result
    
    def BATstrength(self,initial_SOC=0,detAgc=2,scanrate=1):
        '''
        :储能电站的强度分析曲线，若没有储能数据，则无法分析
        :包含储能的运行成本分析
        :输入参数:
        initial_SOC:初始SOC
        detAgc:区分AGC的大小
        scanrate:扫描频率
        :输出参数:
        BatResult:
            'Agc':Agc指令
            '正向调节功率':对应指令下的放电功率和
            '负向调节功率':对应指令下的充电功率和
            '等效2C放电时长':以2C电流放电的等效时长，可反映占空比
            '等效2C充电时长':以2C电流充电的等效时长，可反映占空比
            'DOD':对应指令下的放电深度
            '累积放电深度':对应指令及其之前所有指令的累积放电深度
            'SOC':对应指令结束时刻的剩余电量
        Cost:成本费用，以0.4元/Wh为单位计量 
        elecFee:电费，只含电池系统
        Eqv_cycminus:充电等效循环次数
        Eqv_cycplus:放电等效循环次数
        '''
        Stationname = ['新丰','云河','海丰','河源','鲤鱼江','恒运','宣化','准大','兴和','上都','平朔','同达']
        Cyc_all =     [5000]*12
        Cyc_all = dict(zip(Stationname,Cyc_all))
        Cyc_day =     [  5  ,  8  ,  8  , 8   ,  5   ,  5  ,  5  ,  4  ,  5  ,  8  ,  5  ,  5 ]
        Cyc_day = dict(zip(Stationname,Cyc_day))
        use_electricity_rate = [0.15]*12
        use_electricity_rate = dict(zip(Stationname,use_electricity_rate))
        efficiency = [0.85]*12
        efficiency = dict(zip(Stationname,efficiency))
        soh = [0.80]*12
        soh = dict(zip(Stationname,soh))
        soc = [0.85]*12
        soc = dict(zip(Stationname,soc))
        EPC = [0,0,57189700,52148596,0,0,55051417,0,21585349,0,0,0]
        EPC = dict(zip(Stationname,EPC))
        
        cyc=Cyc_all[self.stationname]
        cyc_day=Cyc_day[self.stationname]
        Capacity=self.BatPe/2
        use_electricity_day=use_electricity_rate[self.stationname]*cyc_day*Capacity
        efficiency=efficiency[self.stationname]
        end_soh=soh[self.stationname]
        EMS_soc=soc[self.stationname]
        EPC=EPC[self.stationname]
        a = cost_perunit(cyc,cyc_day,Capacity,use_electricity_day,efficiency,end_soh,EMS_soc)
        b = a.Initial_investment_cost(EPC)
        if b == -1:
            Cost_unit = 3
        else:
            a.Operation_cost()
            a.Replacement_cost()
            b = a.Unit_cost()
        
        BAT = self.df['Pbat']
        Ee = self.BatPe/2
        BatPe = Ee*2
        AGC = self.Agc
        indexn = self.time
        Length = len(AGC)
        Plus_Pdg = BAT[(BAT>0)].sum()
        Minus_Pdg = BAT[(BAT<0)].sum()
        PlusE_Pdg = Plus_Pdg/3600
        MinusE_Pdg = Minus_Pdg/3600
        Eqv_cycplus = PlusE_Pdg/Ee
        Eqv_cycminus = MinusE_Pdg/Ee
        Bat = pd.DataFrame(columns=['储能充放功率','每次充放倍率','每次充放电量'])
        BatResult = pd.DataFrame(columns=['Agc','正向调节功率','负向调节功率','等效2C放电时长','等效2C充电时长','DOD','累积放电深度','SOC'])
        Bat.iloc[:,0],Bat.iloc[:,1],Bat.iloc[:,2] = BAT,BAT/Ee,BAT/3600
        ctl,Pz,Pf,DOD,Sd,SOC = 0,0,0,0,0,0
        BatResult.loc[ctl] = 0
        Agc,SOC0,i0,ia =AGC[0],initial_SOC,indexn[0],0
        for i in np.arange(0,Length):
            if (indexn[i]-i0).total_seconds()>=scanrate:
                del_t = (indexn[i]-i0).total_seconds()
                if abs(AGC[i]-Agc)>detAgc:
                    DOD = DOD/Ee*100
                    if ctl == 0:
                        Sd = DOD
                        SOC = SOC0 - DOD
                    else:
                        Sd = Sd+DOD
                        SOC = SOC - DOD
                    BatResult.iloc[ctl,0:9] = np.array([Agc,Pz,Pf,Pz/BatPe,Pf/BatPe,DOD,Sd,SOC])
                    ctl = ctl + 1
                    BatResult.loc[ctl] = 0
                    Agc,Pz,Pf,DOD = AGC[i],0,0,0
                else:
                    if BAT[ia]>0:
                        Pz = Pz+BAT[ia]*del_t
                    elif BAT[ia]<0:
                        Pf = Pf+BAT[ia]*del_t
                    for j in range(ia,i):
                        DOD = DOD - BAT[j]*(indexn[j]-indexn[j+1]).total_seconds()/3600
                i0,ia = indexn[i],i
        Cost = Eqv_cycplus*Ee*b
        elecFee = (abs(MinusE_Pdg) - PlusE_Pdg)*0.35*1000
        return BatResult,Cost,elecFee,Eqv_cycminus,Eqv_cycplus
    
    def BATstrength_ems(self,charge1,charge2,discharge1,discharge2,initial_SOC=0,detAgc=2,scanrate=1):
        '''
        :说明:用来对EMS导出数据进行分析,主要是分析储能跟踪情况(现场用),兼顾用来分析从EMS导出的储能调节分析
        :param charge1:储能系统1的可充电功率
        :param charge2:储能系统2的可充电功率
        :param discharge1:储能系统1的可放电功率
        :param discharge2:储能系统2的可放电功率
        :param initial_SOC:初始SOC值
        :param detAgc:AGC指令间的判别条件
        :param scanrate:扫描频率
        
        :return Batresult:电池分析结果（每条指令下的调节总情况)
        :return Cost:成本
        :return elecFee:电费
        :return Eqv_cycminus:等效负循环次数
        :return Eqc_cycplus:等效整循环次数
        :return n:储能由于电量限制，累积未跟踪数
        '''
        BAT = self.df['Pbat']
        PDG = self.Pdg
        Ee = self.BatPe/2
        BatPe = Ee*2
        AGC = self.Agc
        indexn = self.time
        Length = len(AGC)
        Plus_Pdg = BAT[(BAT>0)].sum()
        Minus_Pdg = BAT[(BAT<0)].sum()
        PlusE_Pdg = Plus_Pdg/3600
        MinusE_Pdg = Minus_Pdg/3600
        Eqv_cycplus = PlusE_Pdg/Ee
        Eqv_cycminus = MinusE_Pdg/Ee
        Bat = pd.DataFrame(columns=['储能充放功率','每次充放倍率','每次充放电量'])
        BatResult = pd.DataFrame(columns=['Agc','正向调节功率','负向调节功率','等效2C放电时长','等效2C充电时长','DOD','累积放电深度','SOC','累积未跟踪数'])
        Bat.iloc[:,0],Bat.iloc[:,1],Bat.iloc[:,2] = BAT,BAT/Ee,BAT/3600
        ctl,Pz,Pf,DOD,Sd,SOC = 0,0,0,0,0,0
        BatResult.loc[ctl] = 0
        Agc,SOC0,i0,ia =AGC[0],initial_SOC,indexn[0],0
        n,z = 0,0
        for i in np.arange(0,Length):
            if (indexn[i]-i0).total_seconds()>=scanrate:
                del_t = (indexn[i]-i0).total_seconds()
                if abs(AGC[i]-Agc)>detAgc:
                    DOD = DOD/Ee*100
                    if ctl == 0:
                        Sd = DOD
                        SOC = SOC0 - DOD
                    else:
                        Sd = Sd+DOD
                        SOC = SOC - DOD
                    BatResult.iloc[ctl,0:10] = np.array([Agc,Pz,Pf,Pz/BatPe,Pf/BatPe,DOD,Sd,SOC,n])
                    ctl = ctl + 1
                    BatResult.loc[ctl] = 0
                    Agc,Pz,Pf,DOD = AGC[i],0,0,0
                    z = 0
                else:
                    if BAT[ia]>0:
                        Pz = Pz+BAT[ia]*del_t
                    elif BAT[ia]<0:
                        Pf = Pf+BAT[ia]*del_t
                    for j in range(ia,i):
                        DOD = DOD - BAT[j]*(indexn[j]-indexn[j+1]).total_seconds()/3600
                    if AGC[i]>PDG[i] and z == 0:
                        if discharge1[i]+discharge2[i]<=0.1*BatPe:
                            n += 1
                            z = 1
                    if AGC[i]<PDG[i] and z == 0:
                        if charge1[i]+charge2[i]>=-0.1*BatPe:
                            n += 1
                            z = 1
                i0,ia = indexn[i],i
        Cost = max([Eqv_cycplus,-Eqv_cycminus])/5000*0.4*1000*1000*Ee
        elecFee = (abs(MinusE_Pdg) - PlusE_Pdg)*0.25*1000
        print(n)
        return BatResult,Cost,elecFee,Eqv_cycminus,Eqv_cycplus,n
    
    def PDGstrength(self,detAgc=2,ft_time=10):
        '''
        :输入参数:
        detAgc: 区分AGC的阈值
        ft_time: 反调持续最小时间
        :输出参数:
        Result:有效指令的结果表,字段
            'Agc':AGC
            'Pst':起始时刻Pdg值
            't0':对应时刻
            'Pmov':机组首次动作值
            't1':对应时刻
            'ft':反调
            'bt':不调
            'hm':缓调
            'sw':瞬间完成
            'xg':储能调节是否有效果
            'fx':调节方向
            'end':机组本身是否到达死区
            'Agc-Pst':起始时刻调节缺口   ——8月28日新增
            'Agc-Pend':结束时刻调节缺口  ——8月28日新增
        Op1:机组反调比例
        Op2:机组长时间不动比例
        Op3:机组调节速度小于标准调节速度比例
        Op4:2s内将机组出力拉至AGC上
        S:在有问题调节情况下，储能作用有效的条数
        M:有问题的调节次数
        S/M*100:储能有效调节比例
        '''
        Result = pd.DataFrame(columns=['Agc','Pst','t0','Pmov','t1','ft','bt','hm','sw','xg','fx','end','Agc-Pst','Agc-Pend'])
        #                                0     1     2     3     4    5   6     7    8    9   10    11      12        13
        ctl = 0
        Result.loc[ctl] = 0
        AGC,PDG,Vn = self.Agc,self.Pdg,self.Vn
        Pmov,t1,ft,bt,hm,sw,xg,end = [0]*8
        indexn = self.time
        Agc,Pst,t0 = AGC[0],PDG[0],indexn[0]
        T1,T2i,T2 = [0]*3
        Cdead = 2
        Tlen = 40
        fx = (Agc-Pst)/abs(Agc-Pst)
        Length = len(AGC)
        ft_dead = -0.01*self.Pe # 反调死区
        bt_dead = 0.0007*self.Pe # 不调死区
        jzdz_dead = 0.002*self.Pe # 机组动作死区
        for i in range(0,Length):
            if abs(AGC[i]-Agc)>detAgc:
                if (indexn[i] - t0).total_seconds() >Tlen:
                    if t1 == 0:
                        bt = 1
                    if (ft == 0) and (bt == 0):
                        if end == 0:
                            if (PDG[i] - Pmov)/(indexn[i]-t1).total_seconds()*60<Vn:
                                hm = 1;
                    Result.loc[ctl] = np.array([Agc,Pst,t0,Pmov,t1,ft,bt,hm,sw,xg,fx,end,Agc-Pst,Agc-PDG[i]])
                    ctl = ctl + 1
                    Result.loc[ctl] = 0
                    Agc,Pst,t0 = AGC[i],PDG[i],indexn[i]
                    T1,T2i,T2 = [0]*3
                    Pmov,t1,ft,bt,hm,sw,xg,fx,end = [0]*9
                    fx = (Agc-Pst)/abs(Agc-Pst)
                else:
                    Agc,Pst,t0 = AGC[i],PDG[i],indexn[i]
                    T1,T2i,T2 = [0]*3
                    Pmov,t1,ft,bt,hm,sw,xg,fx,end = [0]*9
                    fx = (Agc-Pst)/abs(Agc-Pst)
            else:
                if (t1 == 0) and (abs(PDG[i]-Pst)>jzdz_dead):
                    Pmov = PDG[i]
                    t1 = indexn[i]
                if i >= 1:
                    fxchange = PDG[i]-Pst
                    if ft == 0:
                        if fxchange*fx<0:
                            T1 = T1+1;
                            if (T1>=ft_time) and fxchange*fx<ft_dead:
                                ft = 1
                                T1 =0
                        else:
                            T1 = 0
                    
                    Change = PDG[i]-PDG[i-1]
                    if (bt ==0) and (t1 != 0):
                        if abs(Agc-PDG[i])>Cdead:
                            if T2i == 0:
                                if abs(Change)<bt_dead:
                                    T2i = indexn[i]
                                    T2 = (indexn[i]-T2i).total_seconds() + 1
                            else:
                                if (abs(Change)<bt_dead) and ((indexn[i]-T2i).total_seconds() ==T2):
                                    T2 = (indexn[i]-T2i).total_seconds().__int__() + 1
                                    if (T2>=Tlen/2) and (abs(PDG[i]-PDG[i-T2])<0.001*self.Pe):
                                        bt =1;
                                        T2 =0
                                        T2i =0
                                else:
                                    T2 =0
                                    T2i =0
                if (indexn[i]-t0).total_seconds()<= 2:
                    if abs(PDG[i] - Agc)<1:
                        sw =1
                if (end == 0) and (abs(Agc-PDG[i])<Cdead):
                    end =1
                if (xg ==0) and (abs(PDG[i]-Agc)<Cdead):
                    xg = 1
        N = len(Result.ix[:,5])
        Op1 = sum(Result.ix[:,5])/N*100 
        Op2 = sum(Result.ix[:,6])/N*100
        Op3 = sum(Result.ix[:,7])/N*100
        Op4 = sum(Result.ix[:,8])/N*100
        M = 0 # 问题调节数量
        S = 0 # 在问题调节下，储能的作用成功响应AGC
        for i in range(N):
            if Result.ix[i,5] == 1 or Result.ix[i,6] == 1 or Result.ix[i,7] == 1:
                M = M + 1
                if Result.ix[i,9] == 1:
                    S = S + 1
        if M != 0:
            K = S/M*100
        else:
            K = 0
        print('反:%.2f\n不动:%.2f\n缓慢:%.2f\n瞬间:%.2f\n非正常调节总次数:%.2f' %(Op1,Op2,Op3,Op4,M))
        return Result,Op1,Op2,Op3,Op4,S,M,K
    
    def agc_static(self,detAgc=2):
        '''
        :用于计算指令持续时间的分布
        :指令缺口的分布(AGC-机组)
        :每条指令下储能最大输出功率及其时间分布
        
        :param detAgc:指令间的判别条件
        
        :return data:分析结果数据，存储指令，指令起始时间，指令缺口大小，储能调节中最大出力及其持续时间
        '''
        Agc = self.Agc
        Pdg = self.Pdg
        Pall = self.Pall
        Pbat = self.Pbat
        time = self.time
        Agc.index = time;Pall.index = time;Pbat.index = time;Pdg.index = time
        AGC0 = Agc[time[0]]
        lasti = time[0]
        if AGC0>Pall[time[0]]:
            flag = 1
            Gap = AGC0 - Pdg[time[0]]
        else:
            flag = -1
            Gap = Pdg[time[0]] - AGC0
        Count = 0
        Max_Count = 0
        record_time = time[0]
        n = 0
        Max = -self.BatPe
        Min = self.BatPe
        data = pd.DataFrame(columns=['指令','指令时间','指令缺口','储能最大出力','最大出力下持续时间'])
        for i in time:
            if abs(Agc[i]-AGC0)>detAgc:
                if flag == 1:
                    data.iloc[n,:] = [AGC0,record_time,Gap,Max,Max_Count]
                else:
                    data.iloc[n,:] = [AGC0,record_time,Gap,Min,Max_Count]
                AGC0 = Agc[i]
                n += 1
                if AGC0>Pall[i]:
                    flag = 1
                    Gap = AGC0 - Pdg[i]
                else:
                    flag = -1
                    Gap = Pdg[i] - AGC0
                Max = -self.BatPe
                Min = self.BatPe
                record_time = time[i]
                Count = 0
                Max_Count = 0
            else:
                if flag == 1:
                    if Count == 0:
                        Max = max(Max,Pbat[i])
                        Count += 1
                    elif Max-self.BatPe*0.015<=Pbat[i]<=Max+self.BatPe*0.025:
                        Count += 1+(i-lasti).seconds
                    elif Pbat[i]>Max+self.BatPe*0.025:
                        Max = max(Max,Pbat[i])
                        Count = 1
                    Max_Count = max(Max_Count,Count)
                else:
                    if Count == 0:
                        Min = min(Min,Pbat[i])
                        Count += 1
                    elif Min+self.BatPe*0.015>=Pbat[i]>=Min-self.BatPe*0.025:
                        Count += 1+(i-lasti).seconds
                    elif Pbat[i]<Min-self.BatPe*0.025:
                        Min = min(Min,Pbat[i])
                        Count = 1
                    Max_Count = max(Max_Count,Count)
            lasti = i
        return data
        
class MX(operation_analyse):
    '''
     :计算蒙西的Kp值和收益
     stationname:电站名称，需要给出
     2019-09-19 修正求取的参数
     '''
    def Kp_Revenue(self,ScanR=5,ADJK1=2.1,minT=30,maxV=5,VarAgc=2,VarPdg=0.01,K1max=4.2,Back=0.02,mink=0.1,maxk=2):
        '''
        :该文档是用来计算蒙西电网K-D-Revenue的函数
        :各参数含义如下：
        AGC:电网下达的AGC功率指令值，功率单位MW，时间间隔1秒
        Pall:联合功率值，功率单位MW，时间间隔为1秒
        RowNum:为计算样本采样点数，时间间隔为1秒，若相邻数据间的间隔不为1秒，请处理源数据，如一天的样本为86400个(秒)
        Prate:机组的额定功率，单位MW，如300MW
        dd1:响应死区系数，如0.012
        dd2:调节死区系数，如0.01
        vc:机组额定速率系数，如0.015倍的机组额定功率
        ts:标准响应时间，单位秒，如60s
        Pn:标准响应偏差系数，如0.008的机组额定功率
        ScanR:扫描频率，单位秒，如5秒
        ADJK1:K1均值上限，如2.1
        minT:有效指令最小持续时长，单位秒，如30秒
        maxV:有效指令最大速度系数，如5倍的额定功率
        VarPdg:有效指令的Agc最小变化量系数，如0.01倍的机组额定功率
        VarAgc:相邻Agc的区分界限，如相差2MW及以上
        K1max:K1最大值，如4.2
        Back:折返系数，如0.02
        mink:k1，k2，k3的最小取值，一般为0.1
        maxk:k2,k3的最大取值，一般为2
            参数返回：
        1——k1
        2——k2
        3——k3
        4——Kp
        5——里程D
        6——收益Revenue
        '''
        if self.stationname in ['新丰','准大','兴和']:
            AGC = self.Agc
            AGC.index = pd.to_datetime(AGC.index,format='%Y-%m-%d %H:%M:%S');AGC=AGC.asfreq(freq='s');AGC.index.freq='s'
            Pall = self.Pall
            Pall.index = pd.to_datetime(Pall.index,format='%Y-%m-%d %H:%M:%S');Pall=Pall.asfreq(freq='s');Pall.index.freq='s'
            Prate = self.Pe
            dd1 = self.deadzone1 
            dd2 = self.deadzone2
            vc = self.Vn/Prate
            ts = self.tn
            Pn = self.detPn
            Result = pd.DataFrame(columns = ['AGC','Pt0','T0','Pt1','T1','Pt2','T2','Pt3','T3',
                                 'Tj','Vj','detP',
                                 'k1','k2','k3','kp','D','flag','Validity'
                                 ])
            ControlNo = 1
            Result.loc[ControlNo] = 0
            Agc,Pt0,T0 = AGC[0],Pall[0],AGC.index[0]
            T1,T2 = 0,0
            if Result.ix[ControlNo,0] > Result.ix[ControlNo,1]:
                flag = [1,1]
            else:
                flag = [-1,-1]
            DeadZone1,DeadZone2 = dd1,dd2
            Vn = Prate*vc
            tn = ts
            detPn = Pn
            Scanrate = ScanR
            ilast = AGC.index[0]
            detP = 0
            for i in AGC.index:
                if not np.isnan(AGC[i]) and not np.isnan(Pall[i]):
                    if (i-ilast).total_seconds() >= Scanrate:
                        if abs(AGC[i]-Agc) >= VarAgc:
                            '''Agc变化，结算上一条指令 的各项k值'''
                            Pt3 = Pall[i]
                            T3 = i
                            if T1 == 0:
                                '''若没有扫描到T1'''
                                Pt1 = Pall[i]
                                T1 = i
                            
                            if T2 == 0:
                                '''若没有扫描到T2'''
                                Pt2 = Pall[i]
                                T2 = i
                            
                            if T2 < T1:
                                '''时间上T1<=T2'''
                                T2 = T1
                            
                            if (ControlNo != 1 and flag[1]*flag[0]>0):
                                '''非折返情况计算里程D'''
                                D = flag[1]*(Pt2-Pt0)
                            elif ControlNo == 1 :
                                D = flag[1]*(Pt2-Pt0)
                            else:
                                '''折返情况计算里程D'''
                                D = flag[1]*(Pt2-Pt0)+Prate*Back
                            
                            T12 = (T2-T1).total_seconds()
                            T03 = (T3-T0).total_seconds()
                            T23 = (T3-T2).total_seconds()
                            
                            if T12 !=0 :
                                '''求取速度V'''
                                Vj = flag[1]*((Pt2-Pt1)/T12)
                                Vj = Vj*60
                            else:
                                if T03 != 0 :
                                    Vj = D/T03
                                    Vj = Vj*60
                                else:
                                    Vj = 0
                            
                            if T03 <= minT or abs(Agc-Pt0) <= Prate*VarPdg or Vj>maxV*Vn:
                                '''
                                :新丰有效指令判断:
                                :规则1:指令时长>30s，
                                :规则2:Agc与初始机组差值>0.01*Prate,
                                :规则3:速度V<5*标准速率，否则记为无效
                                '''
                                Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3 = [0]*9
                                Tj,Vj,detP = [0]*3
                                k1,k2,k3,kp,D,Validity = [0]*6
                            else:
                                '''求k3'''
                                Tj = (T1-T0).total_seconds()
                                k3 = max([mink,maxk-Tj/tn])
                                '''求k1'''
                                k1 = Vj/Vn
                                if k1 > K1max :
                                    k1 = mink
#                                 if k1 < 0.1:
#                                     k1 = mink
                                    
                                if T23 != 0:
                                    '''求detP,进而求k2'''
                                    detP = detP/T23
                                else:
                                    detP = abs(Pt3-Agc)
                                k2 = max([mink,maxk-detP/detPn])
                                '''求kp'''
                                kp = k1*k2*k3
                                Validity = 1
                                '''保存该条指令的记录'''
                                Result.loc[ControlNo] = np.array([Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3,Tj,Vj,detP,k1,k2,k3,kp,D,flag[1],Validity])
                                ControlNo += 1
                                flag[0] = flag[1]
                            '''初始化下一条指令'''
                            Result.loc[ControlNo] = 0
                            Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3 = [0]*9
                            Tj,Vj,detP = [0]*3
                            k1,k2,k3,kp,D,Validity = [0]*6
                            Agc,Pt0,T0 = AGC[i],Pall[i],i
                            if Agc > Pt0:
                                flag[1] = 1
                            else:
                                flag[1] = -1
                        else:
                            if T1 == 0 and abs(Pall[i]-Pt0) >= DeadZone1:
                                '''出响应死区'''
                                Pt1 = Pall[i]
                                T1 = i
                            if T2 == 0 and abs(Pall[i]-Agc) <= DeadZone2:
                                '''进调节死区'''
                                Pt2 = Pall[i]
                                T2 = i
                            if T2 != 0:
                                detP = detP+abs(Pall[i]-Agc)*(i-ilast).total_seconds()
                
                        if i == AGC.index[-1]:
                            '''计算最后时刻点的数据，步骤同上'''
                            Pt3 = Pall[i]
                            T3 = i
                            if T1 == 0 :
                                Pt1 = Pall[i]
                                T1 = i
                            
                            if T2 == 0 :
                                Pt2 = Pall[i]
                                T2 = i
                            
                            T12 = (T2-T1).total_seconds()
                            T03 = (T3-T0).total_seconds()
                            T23 = (T3-T2).total_seconds()
                            
                            if ControlNo != 0 and flag[1]*flag[0]>0 :
                                D = flag[1]*(Pt3-Pt0)
                            else:
                                D = flag[1]*(Pt3-Pt0)+Prate*Back
                                
                            if T12 != 0:
                                Vj = flag[1]*(Pt2-Pt1)/T12
                                Vj = Vj*60
                            else:
                                Vj = D/T03
                                Vj = Vj*60
                            
                            if T03 <= minT or Agc-Pt0 <= Prate*VarPdg or Vj>maxV*Vn:
                                Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3 = [0]*9
                                Tj,Vj,detP = [0]*3
                                k1,k2,k3,kp,D,flag[1],Validity = [0]*7
                                Result.loc[ControlNo] = 0
                            else:
                                Tj = (T1-T0).total_seconds()
                                k3 = max([mink,maxk-Tj/tn])
                                
                                k1 = Vj/Vn
                                if k1 > K1max:
                                    k1 = mink
                                if k1 <0.1:
                                    k1 = 0.1
                                
                                if T23 != 0:
                                    detP = detP/T23
                                else:
                                    detP = abs(Pt3-Agc)
                                
                                k2 = max([mink,maxk-detP/detPn])
                                kp = k1*k2*k3
                                Validity = 1
                                Result.loc[ControlNo] = np.array([Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3,Tj,Vj,detP,k1,k2,k3,kp,D,flag[1],Validity])
                        ilast = i
        else:
            Result.loc[0] = 0
    #     lisrindex = Result[(Result.Validity>0) & (Result.k1>0)].index.tolist()#返回行的名称
        '''计算一日所有结果的平均值作为该日结果'''
        Result1 = Result[(Result.Validity>0)]
        Result2 = Result1[(Result1.k1>0)]
        meank1 = Result2.k1.mean(axis=0)#对k1求平均值
        if meank1 > ADJK1:
            meank1 = meank1-math.floor(meank1*10)/10+ADJK1-0.1
        meank2 = Result2.k2.mean(axis=0)
        meank3 = Result2.k3.mean(axis=0)
        meankp = meank1*meank2*meank3
        sumD = Result1.D.sum()
        Revenue = meankp*sumD*0.02*0.35*1000
#         Result.to_csv(r'C:\Users\JesisW\Desktop\结果.csv',encoding='gbk',header=True,index=False)
        return meank1,meank2,meank3,meankp,sumD,Revenue

class GD(operation_analyse):
    '''
     :计算广东的Kp值和收益
     :2019.11.06 增加对速率的限制条件，>5倍速率判定为异常值
     :param stationname:电站名称，需要给出
    '''
    def Kp_Revenue(self,ScanR=1,VarAgc=0.005,maxk23=1,maxk1=5,TminCon=20,TminVt=30,TminTa=20,TmaxTa=40,TminTR=4,Yagc=12):
        '''
        :该文档是用来计算广东区电站K-D-Revenue的函数
        :各参数含义如下：
        AGC:电网下达的AGC功率指令值，功率单位MW，时间间隔1秒
        Pall:联合功率值，功率单位MW，时间间隔为1秒
        RowNum:为计算样本采样点数，时间间隔为1秒，若相邻数据间的间隔不为1秒，请处理源数据，如一天的样本为86400个(秒)
        Prate:机组的额定功率，单位MW，如300MW
        dd1:响应死区系数，如0.005
        dd2:调节死区系数，如0.005
        vc:机组额定速率系数，如0.015倍的机组额定功率
        ts:标准响应时间，单位秒，如300s
        Pn:标准响应偏差系数，如0.015的机组额定功率
        ScanR:扫描频率，单位秒，如1秒
        VarAgc:相邻Agc的区分界限系数，如0.005
        maxk23:k2,k3的最大取值,如1
        maxk1:k1的最大取值，如5
        TminCon:指令合并时，进入死区最小持续时间，如15s
        TminVt:测速最小持续时间，如30s
        TminTa:进入死区后，最小保持时间，如20s
        TmaxTa:进入死区后，最大测试维持时间，如40s
        TminTR:有效出调节死区最小维持时间，如4s
        Yagc:动态补偿金额
        :参数返回：
        1——k1
        2——k2
        3——k3
        4——Kp
        5——里程D
        6——收益Revenue
        '''
        AGC = self.Agc
        AGC.index = pd.to_datetime(AGC.index,format='%Y-%m-%d %H:%M:%S');AGC=AGC.asfreq(freq='s');AGC.index.freq='s'
        
        Pall = self.Pall
        Pall.index = pd.to_datetime(Pall.index,format='%Y-%m-%d %H:%M:%S');Pall=Pall.asfreq(freq='s');Pall.index.freq='s'
        
        Prate = self.Pe
        dd1 = self.deadzone1
        dd2 = self.deadzone2
        vc = self.Vn/Prate
        ts = self.tn
        Pn = self.detPn
        detAgc = VarAgc*Prate
        Result = pd.DataFrame(columns = ['AGC','Pt0','T0','Pt1','T1','Pt2','T2','Pt3','T3',
                             'Tj','Vj','detP',
                             'k1','k2','k3','kp','Pend','D','flag','Pmax',
                             'Pvst','Tvst','Pvend','Tvend','Validity','Revenue'
                             ])
        Vj = 0
        ControlNo = 1
        Result.loc[ControlNo] = 0
        Agc,Pt0,T0,lasti = AGC[0],Pall[0],AGC.index[0],AGC.index[0]
        T1,T2,T3 = 0,0,0
        k1,k2,k3 = 0,0,0
        Pt1,Pt2,Pt3,detP = 0,0,0,0
        Pend,Pvst,Tvst,Pvend,Tvend = 0,0,0,0,0
#         Psend = 1000
        Psend = 0.7*Agc+0.3*Pt0
        V1 = [0]
        DeadZone1,DeadZone2 = dd1,dd2
        PMAX,PMIN = 0,Prate
        Vn = Prate*vc
        tn = ts
        detPn = Pn
        Scanrate = ScanR
        lastAgc = Pall[0]
        flag = [1,0]
        flag[1] = Agc-Pall[0]
        Psd = max(0.01*Prate,5)
        Psst = Pt0+Psd
        k1set,k2set,k3set = -1,-1,-1
        CountT = 0
        Pt1_temp,T1_temp = 0,0
        V_all = []
        k1_all = []
        Pss = max(Prate*0.01,10)
        for i in AGC.index:
            if not np.isnan(AGC[i]) and not np.isnan(Pall[i]):
                if (i-lasti).total_seconds() >= ScanR:
                    if abs(AGC[i]-Agc) >= detAgc:
                        '''结算上一条Agc指令的k值'''
                        if T2 == 0 or T3 == 0:
                            T = 0
                        else:
                            T = (T3-T2).total_seconds()
                        if ((i-T0).total_seconds()<=2) or (AGC[i]-Pt0)*flag[0]>0 and (AGC[i]-Agc)*flag[0]>0 and T<TminCon:
                            '''合并条件:升出力方向相同；调节方向相同；进入死区时间不足20s，则合并，否则结算'''
                            if Tvst == 0 or Tvend == 0:
                                Tv = 0
                            else:
                                Tv = (Tvend-Tvst).total_seconds()
                            if ControlNo == 1:
                                Result.loc[ControlNo] = 0
                                ControlNo = ControlNo+1
                                Result.loc[ControlNo] = 0
#                                 Psend = 0.7*AGC[i]+0.3*Agc
                                Agc = AGC[i]
                                Pt0 = Pall[i]
                                T0 = i
                                if flag[0]>0:
                                    Psst = Pt0+Psd
                                else:
                                    Psst = Pt0-Psd
                                Psend = 0.7*Agc+0.3*Pt0
                                flag[1] = Agc-Pt0
                            else:
#                                 Psend = 0.7*AGC[i]+0.3*Agc
                                Agc = AGC[i]
                                Pt2 = 0
                                T2 = 0
                                T3 = 0
                                detP = 0
                                if flag[0]>0:
                                    Psst = Pall[i]+Psd
                                else:
                                    Psst = Pall[i]-Psd
                                Psend = 0.7*Agc+0.3*Pall[i]
                                if Tvend == 0:
                                    Pvst,Tvst,Pvend,Tvend = 0,0,0,0
                                else:
                                    if abs(Pvend-Pvst) >=DeadZone2 and Tv>TminTR:
                                        if abs((Pvend-Pvst)/Tv)*60<5*Vn:
                                            if len(V1) == 1 and V1[0] == 0 :
                                                V1 = [abs((Pvend-Pvst)/Tv)*60]
                                            else:
                                                V1.append(abs((Pvend-Pvst)/Tv)*60)
                                            V_all.append(abs((Pvend-Pvst)/Tv)*60)
                                            k1_all.append(min(abs((Pvend-Pvst)/Tv)*60/Vn,5))
                                        else:
                                            if len(V1) == 1 and V1[0] == 0 :
                                                V1 = [5*Vn]
                                            else:
                                                V1.append(5*Vn)
                                            V_all.append(5*Vn)
                                            k1_all.append(5)
                                    else:
                                        if len(V1) == 1 and V1[0] == 0:
                                            V1 = [k1set]
                                        else:
                                            V1.append(k1set)
                            Pvst,Tvst,Pvend,Tvend = 0,0,0,0
                        else:
                            if Tvst == 0 or Tvend == 0:
                                Tv = 0
                            else:
                                Tv = (Tvend-Tvst).total_seconds()
                            if ControlNo == 1:
                                T0,Pt0,T1,Pt2,T2,Pt3,T3 = [0]*7
                                Pt1_temp,T1_temp = 0,0
                                Result.loc[ControlNo] = 0
                                ControlNo = ControlNo+1
                                Result.loc[ControlNo] = 0
#                                 Psend = 0.7*AGC[i]+0.3*Agc
                                Agc = AGC[i]
                                Pt0 = Pall[i]
                                T0 = i
                                if flag[0]>0:
                                    Psst = Pt0+Psd
                                else:
                                    Psst = Pt0-Psd
                                Psend = 0.7*Agc+0.3*Pt0
                                flag[1] = Agc-Pt0
                            else:
                                Pend = Pall[i]
                                if flag[0]>0:
                                    Pmax = PMAX
                                else:
                                    Pmax = PMIN
                                
                                Pt3 = Pall[i]
                                
                                if T1 == 0:
                                    '''计算k2，若没有，则置为0'''
                                    Tj = k2set
                                else:
                                    Tj = (T1-T0).total_seconds()
                                    if Tj<tn:
                                        k2 = maxk23-Tj/tn
                                    else:
                                        Tj = k2set
                                
                                if abs(Agc-Pt0)>Pss*10000:
                                    Vn = 2*Prate*vc
                                else:
                                    Vn = Prate*vc
                                
                                if V1[0] == 0:
                                    if Tvst == 0 or Tvend == 0:
                                        Vj = k1set
                                    else:
                                        if abs(Pvend-Pvst) >=DeadZone2 and Tv>TminTR:
                                            if abs((Pvend-Pvst)/Tv)*60<5*Vn:
                                                Vj = V1 = abs((Pvend-Pvst)/Tv)*60
                                                V_all.append(V1)
                                                k1 = min(maxk1,Vj/Vn)
                                                k1_all.append(k1)
                                            else:
                                                Vj = V1 = 5*Vn
                                                V_all.append(V1)
                                                k1 = min(maxk1,Vj/Vn)
                                                k1_all.append(k1)
                                        else:
                                            Vj = k1set
                                else:
                                    a = []
                                    for m in V1:
                                        if m > 0:
                                            a.append(m)
                                    V1 = a
                                    if Tvst == 0 or Tvend == 0:
                                        if len(V1) == 0:
                                            Vj = k1set
                                        else:
                                            Vj = np.mean(V1)
                                            k1 = min(maxk1,Vj/Vn)
                                    else:
                                        if abs(Pvend-Pvst) >=DeadZone2 and Tv>TminTR:
                                            if abs((Pvend-Pvst)/Tv)*60<5*Vn:
                                                Vj = abs((Pvend-Pvst)/Tv)*60
                                                V_all.append(Vj)
                                                if len(V1) == 0:
                                                    V1 = Vj
                                                else:
                                                    V1.append(Vj)
                                                    Vj = np.mean(V1)
                                            else:
                                                Vj = 5*Vn
                                                V_all.append(Vj)
                                                if len(V1) == 0:
                                                    V1 = Vj
                                                else:
                                                    V1.append(Vj)
                                                    Vj = np.mean(V1)
                                            k1 = min(maxk1,Vj/Vn)
                                            k1_all.append(k1)
                                        else:
                                            if len(V1) == 0:
                                                V1 = k1set
                                            else:
                                                Vj = np.mean(V1)
                                                k1 = min(maxk1,Vj/Vn)
#                                 print(V1)
        #                         if T2-T1>TminVt:
        #                             '''计算k1，若没有，则置为0'''
        #                             Vj = abs(Pt2-Pt0)/(T2-T0)
        #                             Vj = Vj*60
        #                             k1 = min(maxk1,Vj/Vn)
        #                         else:
        #                             Vj = k1set
        #                         
                                if T>TminTa:
                                    '''进入调节死区必须维持20s以上才可计算'''
                                    '''计算k3，若没有，则置为0'''
                                    detP = detP/T*Scanrate
                                    k3 = maxk23-detP/detPn
                                else:
                                    detP = k3set
                                
                                if T1 != 0:
                                    '''计算D，若没有，则置为0'''
                                    if T2 != 0:
                                        D = flag[0]*(Agc - Pt0)
                                    else:
                                        D = Pmax - Pt0
                                else:
                                    D = 0
                                
                                if Vj>0 and Tj>0 and detP>0:
                                    '''若各个指标均有效时计算kp'''
                                    Validity = 1
                                    kp = 0.5*k1+0.25*k2+0.25*k3
                                    Revenue = kp*D*Yagc
                                else:
                                    Validity = 0
                                    kp = 0
                                    Revenue = 0
                                '''保存结果'''
                                Result.loc[ControlNo] = np.array([Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3,Tj,Vj,detP,k1,k2,k3,kp,Pend,D,flag[0],Pmax,Pvst,Tvst,Pvend,Tvend,Validity,Revenue])
                                '''初始化下一条数据'''
                                ControlNo += 1
                                Result.loc[ControlNo] = 0
                                lastAgc = Agc
                                Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3 = [0]*9
                                Tj,Vj,detP = [0]*3
                                k1,k2,k3,kp,D,Validity,Revenue = [0]*7
                                Pend,Pvst,Tvst,Pvend,Tvend = [0]*5
                                V1 = [0]
                                Agc,Pt0,T0 = AGC[i],Pall[i],i
#                                 Psend = 0.7*Agc + 0.3*lastAgc
                                Psend = 0.7*Agc + 0.3*Pt0
                                PMAX,PMIN = 0,Prate
                                Pt1_temp,T1_temp = 0,0
                                if Agc>Pt0:
                                    flag[0] = 1
                                    Psst = Pt0+Psd
                                else:
                                    flag[0] = -1
                                    Psst = Pt0-Psd
                                flag[1] = Agc-lastAgc
                    else:
                        PMAX = max(PMAX,Pall[i])
                        PMIN = min(PMIN,Pall[i])
                        if Pvst == 0:
                            if flag[0]>0:
                                if Pall[i]>Psst:
                                    Pvst = Pall[i]
                                    Tvst = i
                            else:
                                if Pall[i]<Psst:
                                    Pvst = Pall[i]
                                    Tvst = i
                        elif Pvend == 0:
                            if flag[0]>0:
                                if Pall[i]>Psend:
                                    Pvend = Pall[i]
                                    Tvend = i
                            else:
                                if Pall[i]<Psend:
                                    Pvend = Pall[i]
                                    Tvend = i
                        if T1 == 0:
                            if (Agc-Pt0)*(Pall[i]-Pt0)>0:
                                if abs(Pall[i]-Pt0)>DeadZone1:
                                    '''出响应死区并维持4s以上才可以算作出调节死区'''
                                    CountT = CountT+1
                                    if Pt1_temp == 0:
                                        Pt1_temp = Pall[i]
                                        T1_temp = i
                                    if CountT>TminTR:
                                        Pt1 = Pt1_temp
                                        T1 = T1_temp
                                        CountT = 0
                                else:
                                    CountT = 0
                                    Pt1_temp = 0
                                    T1_temp = 0
                                    Pt2 = 0
                                    T2 = 0
                                    T3 = 0
                                    detP = 0
                        if T1_temp !=0 and T2==0 :
                            if Agc>Pt0:
                                if Pall[i]>Agc-DeadZone2:
                                    '''进入调节死区'''
                                    Pt2 = Pall[i]
                                    T2 = i
                            else:
                                if Pall[i]<Agc+DeadZone2:
                                    Pt2 = Pall[i]
                                    T2 = i
                        elif T2 != 0:
                            if (i-T2).total_seconds()<=TmaxTa:
                                '''累加调节精度，最多计数40s'''
                                T3 = i
                                Pt3 = Pall[i]
                                detP = detP+abs(Agc-Pall[i])
                    
                    if i == AGC.index[-1]:
                        Pend = Pall[i]
                        if Tvst == 0 or Tvend == 0:
                            Tv = 0
                        else:
                            Tv = (Tvend-Tvst).total_seconds()
                        if T2 == 0 or T3 == 0:
                            T = 0
                        else:
                            T = (T3-T2).total_seconds()
                        if flag[0]>0:
                            Pmax = PMAX
                        else:
                            Pmax = PMIN
                        
                        Pt3 = Pall[i]
                        
                        if T1 == 0:
                            '''计算k2，若没有，则置为0'''
                            Tj = k2set
                        else:
                            Tj = (T1-T0).total_seconds()
                            if Tj<tn:
                                k2 = maxk23-Tj/tn
                            else:
                                Tj = k2set
                        
                        if V1[0] == 0:
                            if Tvst == 0 or Tvend == 0:
                                Vj = k1set
                            else:
                                if abs(Pvend-Pvst) >=DeadZone2 and Tv>TminTR:
                                    if abs((Pvend-Pvst)/Tv)*60<5*Vn:
                                        Vj = V1 = abs((Pvend-Pvst)/Tv)*60
                                        V_all.append(Vj)
                                        k1 = min(maxk1,Vj/Vn)
                                        k1_all.append(k1)
                                    else:
                                        Vj = V1 = 5*Vn
                                        V_all.append(Vj)
                                        k1 = min(maxk1,Vj/Vn)
                                        k1_all.append(k1)
                                else:
                                    Vj = k1set
                        else:
                            a = []
                            for m in V1:
                                if m>0:
                                    a.append(m)
                            V1 = a
                            if Tvst == 0 or Tvend == 0:
                                if len(V1) == 0:
                                    Vj = k1set
                                else:
                                    Vj = np.mean(V1)
                                    k1 = min(maxk1,Vj/Vn)
                            else:
                                if abs(Pvend-Pvst) >=DeadZone2 and Tv>TminTR:
                                    if abs((Pvend-Pvst)/Tv)*60<5*Vn:
                                        Vj = abs((Pvend-Pvst)/Tv)*60
                                        V_all.append(Vj)
                                        if len(V1) == 0:
                                            V1 = Vj
                                        else:
                                            V1.append(Vj)
                                            Vj = np.mean(V1)
                                    else:
                                        Vj = 5*Vn
                                        V_all.append(Vj)
                                        if len(V1) == 0:
                                            V1 = Vj
                                        else:
                                            V1.append(Vj)
                                            Vj = np.mean(V1)
                                    k1 = min(maxk1,Vj/Vn)
                                    k1_all.append(k1)
                                else:
                                    if len(V1) == 0:
                                        V1 = k1set
                                    else:
                                        Vj = np.mean(V1)
                                        k1 = min(maxk1,Vj/Vn)
                        if T>TminTa:
                            '''进入调节死区必须维持20s以上才可计算'''
                            '''计算k3，若没有，则置为0'''
                            detP = detP/T*Scanrate
                            k3 = maxk23-detP/detPn
                        else:
                            detP = k3set
                         
                        if T1 != 0:
                            '''计算D，若没有，则置为0'''
                            if T2 != 0:
                                D = flag[0]*(Agc - Pt0)
                            else:
                                D = Pmax - Pt0
                        else:
                            D = 0
                        
                        if Vj>0 and Tj>0 and detP>0:
                            '''若各个指标均有效时计算kp'''
                            Validity = 1
                            kp = 0.5*k1+0.25*k2+0.25*k3
                            Revenue = kp*D*Yagc
                        else:
                            Validity = 0
                            kp = 0
                            Revenue = 0
                        '''保存结果'''
#                         Result.loc[ControlNo] = np.array([Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3,Tj,Vj,detP,k1,k2,k3,kp,Pend,D,flag[0],Pmax,Pvst,Tvst,Pvend,Tvend,Validity,Revenue])
                    lasti = i
    #     for j in np.arange(len(Result)):
    #         if Result.loc[j,Vj]>-1:
    #             K1 = K1+Result.loc[j,Vj]
    #             K1Count = K1Count+1
    #         if Result.loc[j,Tj]>-1:
    #             K2 = K2+Result.loc[j,Tj]
    #             K2Count = K2Count+1
    #         if Result.loc[j,detP]>-1:
    #             K3 = K3+Result.loc[j,detP]
    #             K3Count = K3Count+1
#         K1 = Result.Vj[(Result.Vj>-1)].sum()
#         K1Count = len(Result.Vj[(Result.Vj>-1)])
#         K2 = Result.Tj[(Result.Tj>-1)].sum()
#         K2Count = len(Result.Tj[(Result.Tj>-1)])
#         K3 = Result.detP[(Result.detP>-1)].sum()
#         K3Count = len(Result.detP[(Result.detP>-1)])
#         if K1Count == 0:
#             K1Count = 1
#         if K2Count == 0:
#             K2Count = 1
#         if K3Count == 0:
#             K3Count = 1
#         
#         meank1 = min(5,(K1/K1Count)/Vn)
#         meank2 = 1-(K2/K2Count)/tn
#         meank3 = 1-(K3/K3Count)/detPn
#         meankp = 0.5*meank1+0.25*meank2+0.25*meank3
#         sumD = Result.D.sum()
#         Revenue = sumD*meankp*Yagc
        
    #     lisrindex = Result[(Result.Validity>0) & (Result.k1>0)].index.tolist()#返回行的名称
    #     Result1 = Result[(Result.Validity>0)]
    #     Result2 = Result1[(Result1.k1>0)]
        meank1 = Result.k1[(Result.k1>0)].mean()
        meank2 = Result.k2[(Result.k2>0)].mean()
        meank3 = Result.k3[(Result.k3>0)].mean()
        meankp = 0.5*meank1+0.25*meank2+0.25*meank3
        sumD = Result.D.sum()
        print('k1:%.2f \n k2:%.2f \n k3:%.2f \n kp:%.2f \n D:%.2f' %(meank1,meank2,meank3,meankp,sumD))
        Revenue = sumD*meankp*Yagc
#         Result.to_csv(r'C:\Users\JesisW\Desktop\结果.csv',encoding='gbk',header=True,index=False)
        return meank1,meank2,meank3,meankp,sumD,Revenue
    def Kp_Revenue_2018(self,ScanR=1,VarAgc=0.002,maxk23=1,maxk1=5,TminCon=15,TminTa=20,TmaxTa=40,TminTR=4,Yagc=12):
        '''
        :该文档是用来计算广东区电站K-D-Revenue的函数
        :各参数含义如下：
        AGC:电网下达的AGC功率指令值，功率单位MW，时间间隔1秒
        Pall:联合功率值，功率单位MW，时间间隔为1秒
        RowNum:为计算样本采样点数，时间间隔为1秒，若相邻数据间的间隔不为1秒，请处理源数据，如一天的样本为86400个(秒)
        Prate:机组的额定功率，单位MW，如300MW
        dd1:响应死区系数，如0.005
        dd2:调节死区系数，如0.005
        vc:机组额定速率系数，如0.015倍的机组额定功率
        ts:标准响应时间，单位秒，如300s
        Pn:标准响应偏差系数，如0.015的机组额定功率
        ScanR:扫描频率，单位秒，如1秒
        VarAgc:相邻Agc的区分界限系数，如0.005
        maxk23:k2,k3的最大取值,如1
        maxk1:k1的最大取值，如5
        TminCon:指令合并时，进入死区最小持续时间，如15s
        TminVt:测速最小持续时间，如30s
        TminTa:进入死区后，最小保持时间，如20s
        TmaxTa:进入死区后，最大测试维持时间，如40s
        TminTR:有效出调节死区最小维持时间，如4s
        Yagc:动态补偿金额
        参数返回：
        1——k1
        2——k2
        3——k3
        4——Kp
        5——里程D
        6——收益Revenue
        '''
        AGC = self.Agc
        AGC.index = pd.to_datetime(AGC.index,format='%Y-%m-%d %H:%M:%S');AGC = AGC.asfreq(freq='s');AGC.index.freq='s'
        
        Pall = self.Pall
        Pall.index = pd.to_datetime(Pall.index,format='%Y-%m-%d %H:%M:%S');Pall = Pall.asfreq(freq='s');Pall.index.freq='s'
        
        Prate = self.Pe
        DeadZone1,DeadZone2 = self.deadzone1,self.deadzone2
        vc = self.Vn/Prate
        tn = self.tn
        detPn = self.detPn
        detAgc = VarAgc*Prate
        Result = pd.DataFrame(columns = ['AGC','Pt0','T0','Pt1','T1','Pt2','T2','Pt3','T3',
                             'Tj','Vj','detP',
                             'k1','k2','k3','kp','Pend','D','flag','Pmax',
                             'Pvst','Tvst','Pvend','Tvend','Validity','Revenue'
                             ])
        ControlNo = 1
        Result.loc[ControlNo] = 0
        Agc,Pt0,T0,lasti = AGC[0],Pall[0],AGC.index[0],AGC.index[0]
        T1,T2,T3 = 0,0,0
        k1,k2,k3 = 0,0,0
        Pt1,Pt2,Pt3,detP = 0,0,0,0
        Pend,Pvst,Tvst,Pvend,Tvend = 0,0,0,0,0
        Psend = 0.7*Agc+0.3*Pt0
        PMAX,PMIN = 0,Prate
        Vn = Prate*vc
        Scanrate = ScanR
        lastAgc = Pall[0]
        flag = [1,0]
        flag[1] = Agc-Pall[0]
        k1set,k2set,k3set = -1,-1,-1
        CountT = 0
        Psd = max(0.01*Prate,5)
        PTi = max(0.02*Prate*2,20)
        Pt1_temp,T1_temp = 0,0
        Tend_v,Pend_v = T0+int(abs(Agc-Pt0)*60/Vn+Scanrate+1),0
        for i in AGC.index:
            if not np.isnan(AGC[i]) and not np.isnan(Pall[i]):
                if (i-lasti).total_seconds() >= Scanrate:
                    if abs(AGC[i]-Agc) >= detAgc:
                        '''结算上一条Agc指令的k值'''
                        if T2 == 0 or T3 == 0:
                            T = 0
                        else:
                            T = (T3-T2).total_seconds()
                        if ((i-T0).total_seconds()<=2) or ((AGC[i]-Pt0)*flag[0]>0 and (AGC[i]-Agc)*flag[0]>0 and T<=TminCon):
                            '''合并条件:调节方向相同；升出力时，新目标大于上一次；进入死区时间不足15s，则合并，否则结算'''
                            if ControlNo == 1:
                                Result.loc[ControlNo] = 0
                                ControlNo = ControlNo+1
                                Result.loc[ControlNo] = 0
                                Agc = AGC[i]
                                Pt0 = Pall[i]
                                T0 = i
                                Psend = 0.7*Agc+0.3*Pt0
                                Tend_v,Pend_v = T0+int(abs(Agc-Pt0)*60/Vn+Scanrate+1),0
                                flag[1] = Agc-Pt0
                                if Agc>Pt0:
                                    flag[0] = 1
                                else:
                                    flag[0] = -1
                            else:
                                Agc = AGC[i]
                                Pt2 = 0
                                T2 = 0
                                T3 = 0
                                detP = 0
                                Psend = 0.7*Agc+0.3*Pt0                       
                                Tend_v,Pend_v = T0+int(abs(Agc-Pt0)*60/Vn+Scanrate+1),0
                            Pvend,Tvend = 0,0
                        else:
                            if ControlNo == 1:
                                Result.loc[ControlNo] = 0
                                ControlNo = ControlNo+1
                                Result.loc[ControlNo] = 0
                                Agc = AGC[i]
                                Pt0 = Pall[i]
                                T0 = i
                                Psend = 0.7*Agc+0.3*Pt0
                                Tend_v,Pend_v = T0+int(abs(Agc-Pt0)*60/Vn+Scanrate+1),0
                                flag[1] = Agc-Pt0
                                if Agc>Pt0:
                                    flag[0] = 1
                                else:
                                    flag[0] = -1
                            else:
                                Pend = Pall[i]
                                if flag[0]>0:
                                    Pmax = PMAX
                                else:
                                    Pmax = PMIN
                                
                                if T1 == 0:
                                    '''计算k2，若没有，则置为-1'''
                                    Tj = k2set
                                else:
                                    Tj = (T1-T0).total_seconds()
                                    if Tj<tn:
                                        k2 = maxk23-Tj/tn
                                    else:
                                        Tj = k2set
                                
                                if i>Tend_v:
                                    '''计算k1，若没有，则置为-1'''
                                    if Pvst == 0 :
                                        Tvst = T0
                                        Pvst = Pt0
                                    if Pvend == 0:
                                        Tvend = Tend_v
                                        Pvend = Pend_v
                                    
                                    if abs(Pvend-Pvst)>=PTi+1:
                                        Vj = abs(Pvend-Pvst)/(Tvend-Tvst).total_seconds()*60
                                        k1 = min(maxk1,Vj/Vn)
                                    else:
                                        Vj = k1set
                                        k1 = k1set
                                    if T1 !=0 and (Tvend-T1).total_seconds()<=2:
                                        Vj = 15
                                        k1 = min(maxk1,Vj/Vn)
                                else:
                                    Vj = k1set
                                    
                                if T>=TminTa and k2>0:
                                    '''进入调节死区必须维持20s以上才可计算'''
                                    '''计算k3，若没有，则置为-1'''
                                    detP = detP/T*Scanrate
                                    k3 = maxk23-detP/detPn
                                else:
                                    detP = k3set
                                
                                if T1 != 0:
                                    '''计算D，若没有，则置为0'''
                                    if T2 != 0:
                                        D = flag[0]*(Pt2 - Pt0)
                                    else:
                                        D = abs(Pmax - Pt0)
                                else:
                                    D = 0
                                
                                if Vj>0 and Tj>0 and detP>0:
                                    '''若各个指标均有效时计算kp'''
                                    Validity = 1
                                    kp = 0.5*k1+0.25*k2+0.25*k3
                                    Revenue = kp*D*Yagc
                                else:
                                    Validity = 0
                                    kp = 0
                                    Revenue = 0
                                '''保存结果'''
                                Result.loc[ControlNo] = np.array([Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3,Tj,Vj,detP,k1,k2,k3,kp,Pend,D,flag[0],Pmax,Pvst,Tvst,Pvend,Tvend,Validity,Revenue])
                                '''初始化下一条数据'''
                                ControlNo += 1
                                Result.loc[ControlNo] = 0
                                lastAgc = Agc
                                Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3 = [0]*9
                                Tj,Vj,detP = [0]*3
                                k1,k2,k3,kp,D,Validity,Revenue = [0]*7
                                Pend,Pvst,Tvst,Pvend,Tvend = [0]*5
                                Agc,Pt0,T0 = AGC[i],Pall[i],i
                                Psend = 0.7*Agc + 0.3*Pt0
                                PMAX,PMIN = 0,Prate
                                Pt1_temp = 0
                                Tend_v,Pend_v = T0+int(abs(Agc-Pt0)*60/Vn+Scanrate+1),0
                                if Agc>Pt0:
                                    flag[0] = 1
                                else:
                                    flag[0] = -1
                                flag[1] = Agc-lastAgc
                    else:
                        PMAX = max(PMAX,Pall[i])
                        PMIN = min(PMIN,Pall[i])
                        if Pvst == 0:
                            if flag[0]>0:
                                if Pall[i]>Pt0+Psd:
                                    Pvst = Pall[i]
                                    Tvst = i
                            else:
                                if Pall[i]<Pt0-Psd:
                                    Pvst = Pall[i]
                                    Tvst = i
                        elif Pvend == 0:
                            if flag[0]>0:
                                if Pall[i]>Psend:
                                    Pvend = Pall[i]
                                    Tvend = i
                            else:
                                if Pall[i]<Psend:
                                    Pvend = Pall[i]
                                    Tvend = i
                        if Pend_v == 0:
                            if i >= Tend_v:
                                Pend_v = Pall[i]
                        if T1 == 0:
                            if (Agc-Pt0)*(Pall[i]-Pt0)>0:
                                if abs(Pall[i]-Pt0)>DeadZone1:
                                    '''出响应死区并维持4s以上才可以算作出调节死区'''
                                    CountT = CountT+1
                                    if Pt1_temp == 0:
                                        Pt1_temp = Pall[i]
                                        T1_temp = i
                                    if CountT>TminTR:
                                        Pt1 = Pt1_temp
                                        T1 = T1_temp
                                        CountT = 0
                                else:
                                    CountT = 0
                                    Pt1_temp = 0
                                    T1_temp = 0
                                    Pt2 = 0
                                    T2 = 0
                                    T3 = 0
                                    detP = 0
                        if T1_temp !=0 and T2==0 :
                            if Agc>Pt0:
                                if Pall[i]>Agc-DeadZone2:
                                    '''进入调节死区'''
                                    Pt2 = Pall[i]
                                    T2 = i
                            else:
                                if Pall[i]<Agc+DeadZone2:
                                    Pt2 = Pall[i]
                                    T2 = i
                        elif T2 != 0:
                            if (i-T2).total_seconds()<=TmaxTa:
                                '''累加调节精度，最多计数40s'''
                                T3 = i
                                Pt3 = Pall[i]
                                detP = detP+abs(Agc-Pall[i])
                    if i == AGC.index[-1]:
                        Pend = Pall[i]
    
                        if T2 == 0 or T3 == 0:
                            T = 0
                        else:
                            T = (T3-T2).total_seconds()
                        if flag[0]>0:
                            Pmax = PMAX
                        else:
                            Pmax = PMIN
                        
                        if T1 == 0:
                            '''计算k2，若没有，则置为0'''
                            Tj = k2set
                        else:
                            Tj = (T1-T0).total_seconds()
                            if Tj<tn:
                                k2 = maxk23-Tj/tn
                            else:
                                Tj = k2set
                        
                        if i>=Tend_v:
                            '''计算k1，若没有，则置为-1'''
                            if Pvst == 0 :
                                Tvst = T0
                                Pvst = Pt0
                            if Pvend == 0:
                                Tvend = Tend_v
                                Pvend = Pend_v
                            if abs(Pvend-Pvst)>=PTi+1:
                                Vj = abs(Pvend-Pvst)/(Tvend-Tvst).total_seconds()*60
                                k1 = min(maxk1,Vj/Vn)
                            else:
                                Vj = k1set
                                k1 = k1set
                            if T1 !=0 and (Tvend-T1).total_seconds()<=2:
                                Vj = 15
                                k1 = min(maxk1,Vj/Vn)
                        else:
                            k1 = k1set
                            Vj = k1set
                        if T>TminTa:
                            '''进入调节死区必须维持20s以上才可计算'''
                            '''计算k3，若没有，则置为0'''
                            detP = detP/T*Scanrate
                            k3 = maxk23-detP/detPn
                        else:
                            detP = k3set
                         
                        if T1 != 0:
                            '''计算D，若没有，则置为0'''
                            if T2 != 0:
                                D = flag[0]*(Pt2 - Pt0)
                            else:
                                D = abs(Pmax - Pt0)
                        else:
                            D = 0
                        
                        if Vj>0 and Tj>0 and detP>0:
                            '''若各个指标均有效时计算kp'''
                            Validity = 1
                            kp = 0.5*k1+0.25*k2+0.25*k3
                            Revenue = kp*D*Yagc
                        else:
                            Validity = 0
                            kp = 0
                            Revenue = 0
                        '''保存结果'''
                        Result.loc[ControlNo] = np.array([Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3,Tj,Vj,detP,k1,k2,k3,kp,Pend,D,flag[0],Pmax,Pvst,Tvst,Pvend,Tvend,Validity,Revenue])
                    lasti = i        
#         K1 = Result.Vj[(Result.Vj>-1)].sum()
#         K1Count = len(Result.Vj[(Result.Vj>-1)])
#         K2 = Result.Tj[(Result.Tj>-1)].sum()
#         K2Count = len(Result.Tj[(Result.Tj>-1)])
#         K3 = Result.detP[(Result.detP>-1)].sum()
#         K3Count = len(Result.detP[(Result.detP>-1)])
#         if K1Count == 0:
#             K1Count = 1
#         if K2Count == 0:
#             K2Count = 1
#         if K3Count == 0:
#             K3Count = 1
#         meank1 = min(5,(K1/K1Count)/Vn)
#         meank2 = 1-(K2/K2Count)/tn
#         meank3 = 1-(K3/K3Count)/detPn
#         meankp = 0.5*meank1+0.25*meank2+0.25*meank3
#         sumD = Result.D.sum()
#         Revenue = sumD*meankp*Yagc
        meank1 = Result.k1[(Result.k1>0)].mean()
        meank2 = Result.k2[(Result.k2>0)].mean()
        meank3 = Result.k3[(Result.k3>0)].mean()
        meankp = 0.5*meank1+0.25*meank2+0.25*meank3
        sumD = Result.D.sum()
        Revenue = sumD*meankp*Yagc
#         Result.to_csv(r'C:\Users\JesisW\Desktop\结果.csv',encoding='gbk',header=True,index=False)
        return meank1,meank2,meank3,meankp,sumD,Revenue
    def Contribution(self,ScanR=1,VarAgc=0.005,maxk23=1,maxk1=5,TminTa=20,TmaxTa=40,TminTR=4,Yagc=12):
        '''
        该文档是用来计算广东区电站储能出力对完成指令的贡献分析
        各参数含义如下：
        AGC:电网下达的AGC功率指令值，功率单位MW，时间间隔1秒
        Pall:联合功率值，功率单位MW，时间间隔为1秒
        RowNum:为计算样本采样点数，时间间隔为1秒，若相邻数据间的间隔不为1秒，请处理源数据，如一天的样本为86400个(秒)
        Prate:机组的额定功率，单位MW，如300MW
        dd1:响应死区系数，如0.005
        dd2:调节死区系数，如0.005
        vc:机组额定速率系数，如0.015倍的机组额定功率
        ts:标准响应时间，单位秒，如300s
        Pn:标准响应偏差系数，如0.015的机组额定功率
        ScanR:扫描频率，单位秒，如1秒
        VarAgc:相邻Agc的区分界限系数，如0.005
        maxk23:k2,k3的最大取值,如1
        maxk1:k1的最大取值，如5
        TminCon:指令合并时，进入死区最小持续时间，如15s
        TminVt:测速最小持续时间，如30s
        TminTa:进入死区后，最小保持时间，如20s
        TmaxTa:进入死区后，最大测试维持时间，如40s
        TminTR:有效出调节死区最小维持时间，如4s
        Yagc:动态补偿金额
        参数返回：
        1——k1
        2——k2
        3——k3
        4——Kp
        5——里程D
        6——收益Revenue
        '''
        AGC = self.Agc
        AGC.index = pd.to_datetime(AGC.index,format='%Y-%m-%d %H:%M:%S');AGC=AGC.asfreq(freq='s');AGC.index.freq='s'
        
        Pall = self.Pall
        Pall.index = pd.to_datetime(Pall.index,format='%Y-%m-%d %H:%M:%S');Pall=Pall.asfreq(freq='s');Pall.index.freq='s'
        
        Pdg = self.Pdg
        Pdg.index = pd.to_datetime(Pdg.index,format = '%Y-%m-%d %H:%M:%S');Pdg=Pdg.asfreq(freq='s');Pdg.index.freq='s'
        
        Prate = self.Pe
        BatPe = self.BatPe
        dd1 = self.deadzone1
        dd2 = self.deadzone2
        vc = self.Vn/Prate
        ts = self.tn
        Pn = self.detPn
        detAgc = VarAgc*Prate
        Result = pd.DataFrame(columns = ['AGC','Pt0','T0','Pt1','T1','Pt2','T2','Pt3','T3',
                             'Tj','Vj','detP',
                             'k1','k2','k3','kp','Pend','D','flag','Pmax',
                             'Pvst','Tvst','Pvend','Tvend','Validity','Revenue',
                             'Pdg_end','Pbat_end','Pdg_t3','Pbat_t3','Pdg_v','Pbat_v','Pdg_t0'
                             ])
        ControlNo = 1
        Result.loc[ControlNo] = 0
        Agc,Pt0,T0,lasti,Pdg_t0 = AGC[0],Pall[0],AGC.index[0],AGC.index[0],Pdg[0]
        T1,T2,T3,k1,k2,k3,Pt1,Pt2,Pt3,detP = 0,0,0,0,0,0,0,0,0,0
        Pend,Pvst,Tvst,Pvend,Tvend,Pdg_t3,Pbat_t3,Pdg_v,Pbat_v = 0,0,0,0,0,0,0,0,0
        Psend = 0.7*Agc+0.3*Pt0
#         Psend = 1000
        V1 = [0]
        DeadZone1,DeadZone2 = dd1,dd2
        PMAX,PMIN = 0,Prate
        Vn = Prate*vc
        tn = ts
        detPn = Pn
        Scanrate = ScanR
        lastAgc = Pall[0]
        flag = [1,0]
        flag[1] = Agc-Pall[0]
        k1set,k2set,k3set = -1,-1,-1
        CountT = 0
        Psd = max(0.01*Prate,5)
        Pt1_temp,T1_temp = 0,0
        V_all = []
        Pss = max(Prate*0.01,10)
        for i in AGC.index:
            if not np.isnan(AGC[i]) and not np.isnan(Pall[i]):
                if (i-lasti).total_seconds() >= ScanR:
                    if abs(AGC[i]-Agc) >= detAgc:
                        '''结算上一条Agc指令的k值'''
                        if T2 == 0 or T3 == 0:
                            T = 0
                        else:
                            T = (T3-T2).total_seconds()
                        if Tvst == 0 or Tvend == 0:
                            Tv = 0
                        else:
                            Tv = (Tvend-Tvst).total_seconds()
                        if ControlNo == 1:
                            Result.loc[ControlNo] = 0
                            ControlNo = ControlNo+1
                            Result.loc[ControlNo] = 0
#                             Psend = 0.7*AGC[i]+0.3*Agc
                            Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3,Pdg_t3 = [0]*10
                            Pbat_t3,Pdg_v,Pbat_v = [0]*3
                            Agc = AGC[i]
                            Pt0 = Pall[i]
                            T0 = i
                            Psend = 0.7*Agc+0.3*Pt0
                            flag[1] = Agc-Pt0
                        else:
                            Pend = Pall[i]
                            Pdg_end = Pdg[i]
                            Pbat_end = Pall[i]-Pdg[i]
                            if flag[0]>0:
                                Pmax = PMAX
                            else:
                                Pmax = PMIN
                            
                            if T1 == 0:
                                '''计算k2，若没有，则置为0'''
                                Tj = k2set
                            else:
                                Tj = (T1-T0).total_seconds()
                                if Tj<tn:
                                    k2 = maxk23-Tj/tn
                                else:
                                    Tj = k2set
                            
                            if abs(Agc-Pt0)>Pss:
                                Vn = 2*Prate*vc
                            else:
                                Vn = Prate*vc
                            
                            if V1[0] == 0:
                                if Tvst == 0 or Tvend == 0:
                                    Vj = k1set
                                else:
                                    if abs(Pvend-Pvst) >=DeadZone2 and Tv>TminTR:
                                        Vj = V1 = abs((Pvend-Pvst)/Tv)*60
                                        V_all.append(V1)
                                        k1 = min(maxk1,Vj/Vn)
                                    else:
                                        Vj = k1set
                            else:
                                a = []
                                for m in V1:
                                    if m > 0:
                                        a.append(m)
                                V1 = a
                                if Tvst == 0 or Tvend == 0:
                                    if len(V1) == 0:
                                        Vj = k1set
                                    else:
                                        Vj = np.mean(V1)
                                        k1 = min(maxk1,Vj/Vn)
                                else:
                                    if abs(Pvend-Pvst) >=DeadZone2 and Tv>TminTR:
                                        Vj = abs((Pvend-Pvst)/Tv)*60
                                        V_all.append(Vj)
                                        if len(V1) == 0:
                                            V1 = Vj
                                        else:
                                            V1.append(Vj)
                                            Vj = np.mean(V1)
                                        k1 = min(maxk1,Vj/Vn)
                                    else:
                                        if len(V1) == 0:
                                            V1 = k1set
                                        else:
                                            Vj = np.mean(V1)
                                            k1 = min(maxk1,Vj/Vn)
                            if T>TminTa:
                                '''进入调节死区必须维持20s以上才可计算'''
                                '''计算k3，若没有，则置为0'''
                                detP = detP/T*Scanrate
                                k3 = maxk23-detP/detPn
                            else:
                                detP = k3set
                            
                            if T1 != 0:
                                '''计算D，若没有，则置为0'''
                                if T2 != 0:
                                    D = flag[0]*(Agc - Pt0)
                                else:
                                    D = Pmax - Pt0
                            else:
                                D = 0
                            
                            if Vj>0 and Tj>0 and detP>0:
                                '''若各个指标均有效时计算kp'''
                                Validity = 1
                                kp = 0.5*k1+0.25*k2+0.25*k3
                                Revenue = kp*D*Yagc
                            else:
                                Validity = 0
                                kp = 0
                                Revenue = 0
                            '''保存结果'''
                            Result.loc[ControlNo] = np.array([Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3,Tj,Vj,detP,
                                                              k1,k2,k3,kp,Pend,D,flag[0],Pmax,Pvst,Tvst,
                                                              Pvend,Tvend,Validity,Revenue,Pdg_end,Pbat_end,
                                                              Pdg_t3,Pbat_t3,Pdg_v,Pbat_v,Pdg_t0])
                            '''初始化下一条数据'''
                            ControlNo += 1
                            Result.loc[ControlNo] = 0
                            lastAgc = Agc
                            Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3,Pbat_t3,Pdg_t3,Pdg_v,Pbat_v = [0]*13
                            Tj,Vj,detP = [0]*3
                            k1,k2,k3,kp,D,Validity,Revenue = [0]*7
                            Pend,Pvst,Tvst,Pvend,Tvend = [0]*5
                            V1 = [0]
                            Agc,Pt0,T0,Pdg_t0 = AGC[i],Pall[i],i,Pdg[i]
                            Psend = 0.7*Agc + 0.3*Pt0
#                             Psend = 0.7*Agc+0.3*lastAgc
                            PMAX,PMIN = 0,Prate
                            Pt1_temp,T1_temp = 0,0
                            if Agc>Pt0:
                                flag[0] = 1
                            else:
                                flag[0] = -1
                            flag[1] = Agc-lastAgc
                    else:
                        PMAX = max(PMAX,Pall[i])
                        PMIN = min(PMIN,Pall[i])
                        if Pvst == 0:
                            if flag[0]>0:
                                if Pall[i]>Pt0+Psd:
                                    Pvst = Pall[i]
                                    Tvst = i
                            else:
                                if Pall[i]<Pt0-Psd:
                                    Pvst = Pall[i]
                                    Tvst = i
                        elif Pvend == 0:
                            if flag[0]>0:
                                if Pall[i]>Psend:
                                    Pvend = Pall[i]
                                    Tvend = i
                                    Pdg_v = Pdg[i]
                                    Pbat_v = Pall[i]
                            else:
                                if Pall[i]<Psend:
                                    Pvend = Pall[i]
                                    Tvend = i
                                    Pdg_v = Pdg[i]
                                    Pbat_v = Pall[i]
                        if T1 == 0:
                            if (Agc-Pt0)*(Pall[i]-Pt0)>0:
                                if abs(Pall[i]-Pt0)>DeadZone1:
                                    '''出响应死区并维持4s以上才可以算作出调节死区'''
                                    CountT = CountT+1
                                    if Pt1_temp == 0:
                                        Pt1_temp = Pall[i]
                                        T1_temp = i
                                    if CountT>TminTR:
                                        Pt1 = Pt1_temp
                                        T1 = T1_temp
                                        CountT = 0
                                else:
                                    CountT = 0
                                    Pt1_temp = 0
                                    T1_temp = 0
                                    Pt2 = 0
                                    T2 = 0
                                    T3 = 0
                                    detP = 0
                        if T1_temp !=0 and T2==0 :
                            if Agc>Pt0:
                                if Pall[i]>Agc-DeadZone2:
                                    '''进入调节死区'''
                                    Pt2 = Pall[i]
                                    T2 = i
                            else:
                                if Pall[i]<Agc+DeadZone2:
                                    Pt2 = Pall[i]
                                    T2 = i
                        elif T2 != 0:
                            if Pdg_t3 == 0:
                                Pdg_t3 = Pdg[i]
                                Pbat_t3 = Pall[i]-Pdg[i]
                            if (i-T2).total_seconds()<=TmaxTa:
                                '''累加调节精度，最多计数40s'''
                                T3 = i
                                Pt3 = Pall[i]
                                detP = detP+abs(Agc-Pall[i])
                    if i == AGC.index[-1]:
                        Pend = Pall[i]
                        if Tvst == 0 or Tvend == 0:
                            Tv = 0
                        else:
                            Tv = (Tvend-Tvst).total_seconds()
                        if T2 == 0 or T3 == 0:
                            T = 0
                        else:
                            T = (T3-T2).total_seconds()
                        if flag[0]>0:
                            Pmax = PMAX
                        else:
                            Pmax = PMIN
                        
                        Pt3 = Pall[i]
                        
                        if T1 == 0:
                            '''计算k2，若没有，则置为0'''
                            Tj = k2set
                        else:
                            Tj = (T1-T0).total_seconds()
                            if Tj<tn:
                                k2 = maxk23-Tj/tn
                            else:
                                Tj = k2set
                        
                        if V1[0] == 0:
                            if Tvst == 0 or Tvend == 0:
                                Vj = k1set
                            else:
                                if abs(Pvend-Pvst) >=DeadZone2 and Tv>TminTR:
                                    Vj = V1 = abs((Pvend-Pvst)/Tv)*60
                                    V_all.append(Vj)
                                    k1 = min(maxk1,Vj/Vn)
                                else:
                                    Vj = k1set
                        else:
                            a = []
                            for m in V1:
                                if m>0:
                                    a.append(m)
                            V1 = a
                            if Tvst == 0 or Tvend == 0:
                                if len(V1) == 0:
                                    Vj = k1set
                                else:
                                    Vj = np.mean(V1)
                                    k1 = min(maxk1,Vj/Vn)
                            else:
                                if abs(Pvend-Pvst) >=DeadZone2 and Tv>TminTR:
                                    Vj = abs((Pvend-Pvst)/Tv)*60
                                    V_all.append(Vj)
                                    if len(V1) == 0:
                                        V1 = Vj
                                    else:
                                        V1.append(Vj)
                                        Vj = np.mean(V1)
                                    k1 = min(maxk1,Vj/Vn)
                                else:
                                    if len(V1) == 0:
                                        V1 = k1set
                                    else:
                                        Vj = np.mean(V1)
                                        k1 = min(maxk1,Vj/Vn)
                        if T>TminTa:
                            '''进入调节死区必须维持20s以上才可计算'''
                            '''计算k3，若没有，则置为0'''
                            detP = detP/T*Scanrate
                            k3 = maxk23-detP/detPn
                        else:
                            detP = k3set
                         
                        if T1 != 0:
                            '''计算D，若没有，则置为0'''
                            if T2 != 0:
                                D = flag[0]*(Agc - Pt0)
                            else:
                                D = Pmax - Pt0
                        else:
                            D = 0
                        
                        if Vj>0 and Tj>0 and detP>0:
                            '''若各个指标均有效时计算kp'''
                            Validity = 1
                            kp = 0.5*k1+0.25*k2+0.25*k3
                            Revenue = kp*D*Yagc
                        else:
                            Validity = 0
                            kp = 0
                            Revenue = 0
                        '''保存结果'''
                        Result.loc[ControlNo] = np.array([Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3,Tj,Vj,detP,
                                                              k1,k2,k3,kp,Pend,D,flag[0],Pmax,Pvst,Tvst,
                                                              Pvend,Tvend,Validity,Revenue,Pdg_end,Pbat_end,
                                                              Pdg_t3,Pbat_t3,Pdg_v,Pbat_v,Pdg_t0])
                    lasti = i        

#         Result.to_csv(r'C:\Users\JesisW\Desktop\结果.csv',encoding='gbk',header=True,index=False)
        Result.drop(index=1,inplace=True)
#         Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3,Tj,Vj,detP,k1,k2,k3,kp,Pend,D,flag[0],Pmax,Pvst,
#          0   1   2  3   4  5   6  7   8 9  10 11   12 13 14 15  16  17 18      19   20 
#         Tvst,Pvend,Tvend,Validity,Revenue,Pdg_end,Pbat_end,Pdg_t3,Pbat_t3,Pdg_v,Pbat_v,Pdg_t0
#         21    22    23     24      25        26      27      28     29      30     31    32
#         指令持续时间,大于40MW,存在k1或k3,进入死区不足20s,未进死区,机组反调
#             33       34      35        36         37    38
        Result['指令持续时间'] = 0;Result['小于40MW'] = 0;Result['存在k1或k3'] = 0
        for i in np.arange(len(Result)-1):
            Result.iloc[i,33] = (Result.iloc[i,2]-Result.iloc[i+1,2]).total_seconds()
            if Result.iloc[i,0]-Result.iloc[i,32]<=40: #Result.iloc[i,32]是以机组功率为40MW分割;Result.iloc[i,1]是以联合功率为40MW分割
                Result.iloc[i,34] = 1
            else:
                Result.iloc[i,34] = 0
            if Result.iloc[i,12]>0 or Result.iloc[i,14]>0:
                Result.iloc[i,35] = 1
            else:
                Result.iloc[i,35] = 0
        Result = Result[Result['指令持续时间']<=-5]
        print('指令缺口小于40MW的条数：%.2f' %len(Result[(Result['小于40MW']==1)]))
        df = Result[(Result['小于40MW']==1) & (Result['存在k1或k3']==1)]
        print('指令缺口小于40MW且存在k1或k3的条数：%.2f' %len(df))
        meank1 = df[df['k1']>0].mean().k1;meank2 = df[df['k2']>0].mean().k2;meank3 = df[df['k3']>0].mean().k3;meankp=meank1*0.5+meank2*0.25+meank3*0.25
        print('k1=%.2f ;k2=%.2f ;k3=%.2f;kp=%.2f' %(meank1,meank2,meank3,meankp))
        Result_reason = Result[(Result['小于40MW']==1) & (Result['存在k1或k3']==0)]
        Result_reason['进入死区不足20s']=0;Result_reason['未进死区']=0;Result_reason['机组反调']=0
        for i in np.arange(len(Result_reason)):
            if (Result_reason.iloc[i,26]-Result_reason.iloc[i,32])*Result_reason.iloc[i,18]<0:
                Result_reason.iloc[i,38] = 1
            if (Result_reason.iloc[i,8] !=0):
                Result_reason.iloc[i,36]=1
            else:
                if abs((Result_reason.iloc[i,1]-Result_reason.iloc[i,32])-Result_reason.iloc[i,27])>5:
                    Result_reason.iloc[i,37]=1 # 未进死区且储能变化小于5MW
        print('指令缺口小于40MW但不存在k1和k3:%.2f' %len(Result_reason))
        print('到达死区没有维持20s:%.2f;未到达死区:%.2f;机组反向贡献:%.2f' %(sum(Result_reason['进入死区不足20s']),sum(Result_reason['未进死区']),sum(Result_reason['机组反调'])))
        Result_contribution = pd.DataFrame(columns=['联合到达死区','储能贡献','机组贡献','flag','储能贡献度','机组贡献度','时间'])
        for i in np.arange(len(Result)):
            Result_contribution.loc[i]=0
            Result_contribution.iloc[i,6] = Result.iloc[i,2]
            Result_contribution.iloc[i,3] = Result.iloc[i,18]
            if abs(Result.iloc[i,5]-Result.iloc[i,0])<=DeadZone2:
                Result_contribution.iloc[i,0]=1
                Result_contribution.iloc[i,1]=Result.iloc[i,29]-(Result.iloc[i,1]-Result.iloc[i,32])
                Result_contribution.iloc[i,2]=Result.iloc[i,28]-Result.iloc[i,32]
                if abs(Result_contribution.iloc[i,2])>100:
                    Result_contribution.iloc[i,2]=Result.iloc[i,26]-Result.iloc[i,32]
            else:
                Result_contribution.iloc[i,0]=0
                Result_contribution.iloc[i,1]=Result.iloc[i,27]-(Result.iloc[i,1]-Result.iloc[i,32])
                Result_contribution.iloc[i,2]=Result.iloc[i,26]-Result.iloc[i,32]
            # 采用调节功率作为贡献基数
            Result_contribution.iloc[i,4] = Result_contribution.iloc[i,1]/(Result.iloc[i,0]-Result.iloc[i,1])*100
            Result_contribution.iloc[i,5] = Result_contribution.iloc[i,2]/(Result.iloc[i,0]-Result.iloc[i,1])*100
            Result_contribution.iloc[i,1]=Result_contribution.iloc[i,1]*Result_contribution.iloc[i,3]
            Result_contribution.iloc[i,2]=Result_contribution.iloc[i,2]*Result_contribution.iloc[i,3]
            # 采用机组和储能的加和功率作为贡献基数
#             Result_contribution.iloc[i,1]=Result_contribution.iloc[i,1]*Result_contribution.iloc[i,3]
#             Result_contribution.iloc[i,2]=Result_contribution.iloc[i,2]*Result_contribution.iloc[i,3]
#             M = Result_contribution.iloc[i,1]+Result_contribution.iloc[i,2]
#             if Result_contribution.iloc[i,1]<0 and Result_contribution.iloc[i,2]<0:
#                 Result_contribution.iloc[i,4] = Result_contribution.iloc[i,1]/M*100*(-1)
#                 Result_contribution.iloc[i,5] = Result_contribution.iloc[i,2]/M*100*(-1)
#             else:
#                 Result_contribution.iloc[i,4] = Result_contribution.iloc[i,1]/M*100
#                 Result_contribution.iloc[i,5] = Result_contribution.iloc[i,2]/M*100
        Result_contribution.to_csv(r'C:\Users\JesisW\Desktop\贡献度结果表.csv',encoding='gbk',header=True)
        Result.to_csv(r'C:\Users\JesisW\Desktop\去掉5s以内变化的AGC指令的结果表.csv',encoding='gbk',header=True)
        Result_reason.to_csv(r'C:\Users\JesisW\Desktop\在40MW以内的指令中没有有效k1或k3的原因结果表.csv',encoding='gbk',header=True)
        return Result
    def Kp_Revenue_2019(self,ScanR=1,VarAgc=0.005,maxk23=1,maxk1=5,TminCon=15,TminVt=30,TminTa=20,TmaxTa=40,TminTR=4,Yagc=12):
        '''
        :该文档是用来计算广东区电站K-D-Revenue的函数
        :各参数含义如下：
        AGC:电网下达的AGC功率指令值，功率单位MW，时间间隔1秒
        Pall:联合功率值，功率单位MW，时间间隔为1秒
        RowNum:为计算样本采样点数，时间间隔为1秒，若相邻数据间的间隔不为1秒，请处理源数据，如一天的样本为86400个(秒)
        Prate:机组的额定功率，单位MW，如300MW
        dd1:响应死区系数，如0.005
        dd2:调节死区系数，如0.005
        vc:机组额定速率系数，如0.015倍的机组额定功率
        ts:标准响应时间，单位秒，如300s
        Pn:标准响应偏差系数，如0.015的机组额定功率
        ScanR:扫描频率，单位秒，如1秒
        VarAgc:相邻Agc的区分界限系数，如0.005
        maxk23:k2,k3的最大取值,如1
        maxk1:k1的最大取值，如5
        TminCon:指令合并时，进入死区最小持续时间，如15s
        TminVt:测速最小持续时间，如30s
        TminTa:进入死区后，最小保持时间，如20s
        TmaxTa:进入死区后，最大测试维持时间，如40s
        TminTR:有效出调节死区最小维持时间，如4s
        Yagc:动态补偿金额
        :参数返回：
        1——k1
        2——k2
        3——k3
        4——Kp
        5——里程D
        6——收益Revenue
        '''
        AGC = self.Agc
        AGC.index = pd.to_datetime(AGC.index,format='%Y-%m-%d %H:%M:%S');AGC=AGC.asfreq(freq='s');AGC.index.freq='s'
        
        Pall = self.Pall
        Pall.index = pd.to_datetime(Pall.index,format='%Y-%m-%d %H:%M:%S');Pall=Pall.asfreq(freq='s');Pall.index.freq='s'
        
        Prate = self.Pe
        dd1 = self.deadzone1
        dd2 = self.deadzone2
        vc = self.Vn/Prate
        ts = self.tn
        Pn = self.detPn
        detAgc = VarAgc*Prate
        Result = pd.DataFrame(columns = ['AGC','Pt0','T0','Pt1','T1','Pt2','T2','Pt3','T3',
                             'Tj','Vj','detP',
                             'k1','k2','k3','kp','Pend','D','flag','Pmax',
                             'Pvst','Tvst','Pvend','Tvend','Validity','Revenue'
                             ])
        Vj = 0
        ControlNo = 1
        Result.loc[ControlNo] = 0
        Agc,Pt0,T0,lasti = AGC[0],Pall[0],AGC.index[0],AGC.index[0]
        T1,T2,T3 = 0,0,0
        k1,k2,k3 = 0,0,0
        Pt1,Pt2,Pt3,detP = 0,0,0,0
        Pend,Pvst,Tvst,Pvend,Tvend = 0,0,0,0,0
#         Psend = 1000
        Psend = 0.7*Agc+0.3*Pt0
        V1 = [0]
        DeadZone1,DeadZone2 = dd1,dd2
        PMAX,PMIN = 0,Prate
        Vn = Prate*vc
        tn = ts
        detPn = Pn
        Scanrate = ScanR
        lastAgc = Pall[0]
        flag = [1,0]
        flag[1] = Agc-Pall[0]
        Psd = max(0.01*Prate,5)
        Psst = Pt0+Psd
        k1set,k2set,k3set = -1,-1,-1
        CountT = 0
        Pt1_temp,T1_temp = 0,0
        V_all = []
        Pss = max(Prate*0.01,10)
        for i in AGC.index:
            if not np.isnan(AGC[i]) and not np.isnan(Pall[i]):
                if (i-lasti).total_seconds() >= ScanR:
                    if abs(AGC[i]-Agc) >= detAgc:
                        '''结算上一条Agc指令的k值'''
                        if T2 == 0 or T3 == 0:
                            T = 0
                        else:
                            T = (T3-T2).total_seconds()
                        if ((i-T0).total_seconds()<=2) or (AGC[i]-Pt0)*flag[0]>0 and (AGC[i]-Agc)*flag[0]>0 and T<TminCon and (i-T0).total_seconds()<120:
                            '''合并条件:升出力方向相同；调节方向相同；进入死区时间不足20s;本条与上条指令下发时间在120s内，则合并，否则结算'''
                            if Tvst == 0 or Tvend == 0:
                                Tv = 0
                            else:
                                Tv = (Tvend-Tvst).total_seconds()
                            if ControlNo == 1:
                                Result.loc[ControlNo] = 0
                                ControlNo = ControlNo+1
                                Result.loc[ControlNo] = 0
#                                 Psend = 0.7*AGC[i]+0.3*Agc
                                Agc = AGC[i]
                                Pt0 = Pall[i]
                                T0 = i
                                if flag[0]>0:
                                    Psst = Pt0+Psd
                                else:
                                    Psst = Pt0-Psd
                                Psend = 0.7*Agc+0.3*Pt0
                                flag[1] = Agc-Pt0
                            else:
#                                 Psend = 0.7*AGC[i]+0.3*Agc
                                Agc = AGC[i]
                                Pt2 = 0
                                T2 = 0
                                T3 = 0
                                detP = 0
                                if flag[0]>0:
                                    Psst = Pall[i]+Psd
                                else:
                                    Psst = Pall[i]-Psd
                                Psend = 0.7*Agc+0.3*Pall[i]
                                if Tvend == 0:
                                    Pvst,Tvst,Pvend,Tvend = 0,0,0,0
                                else:
                                    if abs(Pvend-Pvst) >=DeadZone2 and Tv>TminTR:
                                        if abs((Pvend-Pvst)/Tv)*60<5*Vn:
                                            if len(V1) == 1 and V1[0] == 0 :
                                                V1 = [abs((Pvend-Pvst)/Tv)*60]
                                            else:
                                                V1.append(abs((Pvend-Pvst)/Tv)*60)
                                            V_all.append(abs((Pvend-Pvst)/Tv)*60)
                                    else:
                                        if len(V1) == 1 and V1[0] == 0:
                                            V1 = [k1set]
                                        else:
                                            V1.append(k1set)
                            Pvst,Tvst,Pvend,Tvend = 0,0,0,0
                        else:
                            if Tvst == 0 or Tvend == 0:
                                Tv = 0
                            else:
                                Tv = (Tvend-Tvst).total_seconds()
                            if ControlNo == 1:
                                T0,Pt0,T1,Pt2,T2,Pt3,T3 = [0]*7
                                Pt1_temp,T1_temp = 0,0
                                Result.loc[ControlNo] = 0
                                ControlNo = ControlNo+1
                                Result.loc[ControlNo] = 0
#                                 Psend = 0.7*AGC[i]+0.3*Agc
                                Agc = AGC[i]
                                Pt0 = Pall[i]
                                T0 = i
                                if flag[0]>0:
                                    Psst = Pt0+Psd
                                else:
                                    Psst = Pt0-Psd
                                Psend = 0.7*Agc+0.3*Pt0
                                flag[1] = Agc-Pt0
                            else:
                                Pend = Pall[i]
                                if flag[0]>0:
                                    Pmax = PMAX
                                else:
                                    Pmax = PMIN
                                
                                Pt3 = Pall[i]
                                
                                if T1 == 0:
                                    '''计算k2，若没有，则置为0'''
                                    Tj = k2set
                                else:
                                    Tj = (T1-T0).total_seconds()
                                    if Tj<tn:
                                        k2 = maxk23-Tj/tn
                                    else:
                                        Tj = k2set
                                
                                if abs(Agc-Pt0)>Pss*10000:
                                    Vn = 2*Prate*vc
                                else:
                                    Vn = Prate*vc
                                
                                if V1[0] == 0:
                                    if Tvst == 0 or Tvend == 0:
                                        Vj = k1set
                                    else:
                                        if abs(Pvend-Pvst) >=DeadZone2 and Tv>TminTR:
                                            if abs((Pvend-Pvst)/Tv)*60<5*Vn:
                                                Vj = V1 = abs((Pvend-Pvst)/Tv)*60
                                                V_all.append(V1)
                                                k1 = min(maxk1,Vj/Vn)
                                        else:
                                            Vj = k1set
                                else:
                                    a = []
                                    for m in V1:
                                        if m > 0:
                                            a.append(m)
                                    V1 = a
                                    if Tvst == 0 or Tvend == 0:
                                        if len(V1) == 0:
                                            Vj = k1set
                                        else:
                                            Vj = np.mean(V1)
                                            k1 = min(maxk1,Vj/Vn)
                                    else:
                                        if abs(Pvend-Pvst) >=DeadZone2 and Tv>TminTR:
                                            if abs((Pvend-Pvst)/Tv)*60<5*Vn:
                                                Vj = abs((Pvend-Pvst)/Tv)*60
                                                V_all.append(Vj)
                                                if len(V1) == 0:
                                                    V1 = Vj
                                                else:
                                                    V1.append(Vj)
                                                    Vj = np.mean(V1)
                                            k1 = min(maxk1,Vj/Vn)
                                        else:
                                            if len(V1) == 0:
                                                V1 = k1set
                                            else:
                                                Vj = np.mean(V1)
                                                k1 = min(maxk1,Vj/Vn)
#                                 print(V1)
        #                         if T2-T1>TminVt:
        #                             '''计算k1，若没有，则置为0'''
        #                             Vj = abs(Pt2-Pt0)/(T2-T0)
        #                             Vj = Vj*60
        #                             k1 = min(maxk1,Vj/Vn)
        #                         else:
        #                             Vj = k1set
        #                         
                                if T>TminTa:
                                    '''进入调节死区必须维持20s以上才可计算'''
                                    '''计算k3，若没有，则置为0'''
                                    detP = detP/T*Scanrate
                                    k3 = maxk23-detP/detPn
                                else:
                                    detP = k3set
                                
                                if T1 != 0:
                                    '''计算D，若没有，则置为0'''
                                    if T2 != 0:
                                        D = flag[0]*(Agc - Pt0)
                                    else:
                                        D = Pmax - Pt0
                                else:
                                    D = 0
                                
                                if Vj>0 and Tj>0 and detP>0:
                                    '''若各个指标均有效时计算kp'''
                                    Validity = 1
                                    kp = 0.5*k1+0.25*k2+0.25*k3
                                    Revenue = kp*D*Yagc
                                else:
                                    Validity = 0
                                    kp = 0
                                    Revenue = 0
                                '''保存结果'''
                                Result.loc[ControlNo] = np.array([Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3,Tj,Vj,detP,k1,k2,k3,kp,Pend,D,flag[0],Pmax,Pvst,Tvst,Pvend,Tvend,Validity,Revenue])
                                '''初始化下一条数据'''
                                ControlNo += 1
                                Result.loc[ControlNo] = 0
                                lastAgc = Agc
                                Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3 = [0]*9
                                Tj,Vj,detP = [0]*3
                                k1,k2,k3,kp,D,Validity,Revenue = [0]*7
                                Pend,Pvst,Tvst,Pvend,Tvend = [0]*5
                                V1 = [0]
                                Agc,Pt0,T0 = AGC[i],Pall[i],i
#                                 Psend = 0.7*Agc + 0.3*lastAgc
                                Psend = 0.7*Agc + 0.3*Pt0
                                PMAX,PMIN = 0,Prate
                                Pt1_temp,T1_temp = 0,0
                                if Agc>Pt0:
                                    flag[0] = 1
                                    Psst = Pt0+Psd
                                else:
                                    flag[0] = -1
                                    Psst = Pt0-Psd
                                flag[1] = Agc-lastAgc
                    else:
                        PMAX = max(PMAX,Pall[i])
                        PMIN = min(PMIN,Pall[i])
                        if Pvst == 0:
                            if flag[0]>0:
                                if Pall[i]>Psst:
                                    Pvst = Pall[i]
                                    Tvst = i
                            else:
                                if Pall[i]<Psst:
                                    Pvst = Pall[i]
                                    Tvst = i
                        elif Pvend == 0:
                            if flag[0]>0:
                                if Pall[i]>Psend:
                                    Pvend = Pall[i]
                                    Tvend = i
                            else:
                                if Pall[i]<Psend:
                                    Pvend = Pall[i]
                                    Tvend = i
                        if T1 == 0:
                            if (Agc-Pt0)*(Pall[i]-Pt0)>0:
                                if abs(Pall[i]-Pt0)>DeadZone1:
                                    '''出响应死区并维持4s以上才可以算作出调节死区'''
                                    CountT = CountT+1
                                    if Pt1_temp == 0:
                                        Pt1_temp = Pall[i]
                                        T1_temp = i
                                    if CountT>TminTR:
                                        Pt1 = Pt1_temp
                                        T1 = T1_temp
                                        CountT = 0
                                else:
                                    CountT = 0
                                    Pt1_temp = 0
                                    T1_temp = 0
                                    Pt2 = 0
                                    T2 = 0
                                    T3 = 0
                                    detP = 0
                        if T1_temp !=0 and T2==0 :
                            if Agc>Pt0:
                                if Pall[i]>Agc-DeadZone2:
                                    '''进入调节死区'''
                                    Pt2 = Pall[i]
                                    T2 = i
                            else:
                                if Pall[i]<Agc+DeadZone2:
                                    Pt2 = Pall[i]
                                    T2 = i
                        elif T2 != 0:
                            if (i-T2).total_seconds()<=TmaxTa:
                                '''累加调节精度，最多计数40s'''
                                T3 = i
                                Pt3 = Pall[i]
                                detP = detP+abs(Agc-Pall[i])
                    
                    if i == AGC.index[-1]:
                        Pend = Pall[i]
                        if Tvst == 0 or Tvend == 0:
                            Tv = 0
                        else:
                            Tv = (Tvend-Tvst).total_seconds()
                        if T2 == 0 or T3 == 0:
                            T = 0
                        else:
                            T = (T3-T2).total_seconds()
                        if flag[0]>0:
                            Pmax = PMAX
                        else:
                            Pmax = PMIN
                        
                        Pt3 = Pall[i]
                        
                        if T1 == 0:
                            '''计算k2，若没有，则置为0'''
                            Tj = k2set
                        else:
                            Tj = (T1-T0).total_seconds()
                            if Tj<tn:
                                k2 = maxk23-Tj/tn
                            else:
                                Tj = k2set
                        
                        if V1[0] == 0:
                            if Tvst == 0 or Tvend == 0:
                                Vj = k1set
                            else:
                                if abs(Pvend-Pvst) >=DeadZone2 and Tv>TminTR:
                                    if abs((Pvend-Pvst)/Tv)*60<5*Vn:
                                        Vj = V1 = abs((Pvend-Pvst)/Tv)*60
                                        V_all.append(Vj)
                                        k1 = min(maxk1,Vj/Vn)
                                else:
                                    Vj = k1set
                        else:
                            a = []
                            for m in V1:
                                if m>0:
                                    a.append(m)
                            V1 = a
                            if Tvst == 0 or Tvend == 0:
                                if len(V1) == 0:
                                    Vj = k1set
                                else:
                                    Vj = np.mean(V1)
                                    k1 = min(maxk1,Vj/Vn)
                            else:
                                if abs(Pvend-Pvst) >=DeadZone2 and Tv>TminTR:
                                    if abs((Pvend-Pvst)/Tv)*60<5*Vn:
                                        Vj = abs((Pvend-Pvst)/Tv)*60
                                        V_all.append(Vj)
                                        if len(V1) == 0:
                                            V1 = Vj
                                        else:
                                            V1.append(Vj)
                                            Vj = np.mean(V1)
                                    k1 = min(maxk1,Vj/Vn)
                                else:
                                    if len(V1) == 0:
                                        V1 = k1set
                                    else:
                                        Vj = np.mean(V1)
                                        k1 = min(maxk1,Vj/Vn)
#                         print(V1)
                        if T>TminTa:
                            '''进入调节死区必须维持20s以上才可计算'''
                            '''计算k3，若没有，则置为0'''
                            detP = detP/T*Scanrate
                            k3 = maxk23-detP/detPn
                        else:
                            detP = k3set
                         
                        if T1 != 0:
                            '''计算D，若没有，则置为0'''
                            if T2 != 0:
                                D = flag[0]*(Agc - Pt0)
                            else:
                                D = Pmax - Pt0
                        else:
                            D = 0
                        
                        if Vj>0 and Tj>0 and detP>0:
                            '''若各个指标均有效时计算kp'''
                            Validity = 1
                            kp = 0.5*k1+0.25*k2+0.25*k3
                            Revenue = kp*D*Yagc
                        else:
                            Validity = 0
                            kp = 0
                            Revenue = 0
                        '''保存结果'''
#                         Result.loc[ControlNo] = np.array([Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3,Tj,Vj,detP,k1,k2,k3,kp,Pend,D,flag[0],Pmax,Pvst,Tvst,Pvend,Tvend,Validity,Revenue])
                    lasti = i
    #     for j in np.arange(len(Result)):
    #         if Result.loc[j,Vj]>-1:
    #             K1 = K1+Result.loc[j,Vj]
    #             K1Count = K1Count+1
    #         if Result.loc[j,Tj]>-1:
    #             K2 = K2+Result.loc[j,Tj]
    #             K2Count = K2Count+1
    #         if Result.loc[j,detP]>-1:
    #             K3 = K3+Result.loc[j,detP]
    #             K3Count = K3Count+1
#         K1 = Result.Vj[(Result.Vj>-1)].sum()
#         K1Count = len(Result.Vj[(Result.Vj>-1)])
#         K2 = Result.Tj[(Result.Tj>-1)].sum()
#         K2Count = len(Result.Tj[(Result.Tj>-1)])
#         K3 = Result.detP[(Result.detP>-1)].sum()
#         K3Count = len(Result.detP[(Result.detP>-1)])
#         if K1Count == 0:
#             K1Count = 1
#         if K2Count == 0:
#             K2Count = 1
#         if K3Count == 0:
#             K3Count = 1
#         
#         meank1 = min(5,(K1/K1Count)/Vn)
#         meank2 = 1-(K2/K2Count)/tn
#         meank3 = 1-(K3/K3Count)/detPn
#         meankp = 0.5*meank1+0.25*meank2+0.25*meank3
#         sumD = Result.D.sum()
#         Revenue = sumD*meankp*Yagc
        
    #     lisrindex = Result[(Result.Validity>0) & (Result.k1>0)].index.tolist()#返回行的名称
    #     Result1 = Result[(Result.Validity>0)]
    #     Result2 = Result1[(Result1.k1>0)]
        meank1 = Result.k1[(Result.k1>0)].mean()
        meank2 = Result.k2[(Result.k2>0)].mean()
        meank3 = Result.k3[(Result.k3>0)].mean()
        meankp = 0.5*meank1+0.25*meank2+0.25*meank3
        sumD = Result.D.sum()
        print('k1:%.2f \n k2:%.2f \n k3:%.2f \n kp:%.2f \n D:%.2f' %(meank1,meank2,meank3,meankp,sumD))
        Revenue = sumD*meankp*Yagc
#         Result.to_csv(r'C:\Users\JesisW\Desktop\结果.csv',encoding='gbk',header=True,index=False)
        return meank1,meank2,meank3,meankp,sumD,Revenue
        
class HB(operation_analyse):
    '''
     :计算华北的Kp值和收益
     stationname:电站名称，需要给出
    '''
    def Kp_Revenue(self,ScanR=5,VarAgc=5,Back=0.02,mink=0.1,maxk=2,Yagc=5):

        '''
        :该文档是用来计算华北区电站K-D-Revenue的函数
        :各参数含义如下：
        AGC:电网下达的AGC功率指令值，功率单位MW，时间间隔1秒
        Pall:联合功率值，功率单位MW，时间间隔为1秒
        RowNum:为计算样本采样点数，时间间隔为1秒，若相邻数据间的间隔不为1秒，请处理源数据，如一天的样本为86400个(秒)
        Prate:机组的额定功率，单位MW，如300MW
        dd1:响应死区系数
        dd2:调节死区系数
        vc:机组额定速率系数，如0.015倍的机组额定功率
        ts:标准响应时间，单位秒，如60s
        Pn:标准响应偏差系数，如0.008的机组额定功率
        ScanR:扫描频率，单位秒，如5秒
        VarAgc:相邻Agc的区分界限，如相差5MW及以上
        Back:折返系数，如0.02(2%)
        mink:k1，k2，k3的最小取值，一般为0.1
        maxk:k2,k3的最大取值，一般为2
        Yagc:单位补偿金额，5元/MW
            参数返回：
        1——k1
        2——k2
        3——k3
        4——Kp
        5——里程D
        6——收益Revenue
        '''
        AGC = self.Agc
        AGC.index = pd.to_datetime(AGC.index,format='%Y-%m-%d %H:%M:%S');AGC=AGC.asfreq(freq='s');AGC.index.freq='s'
        Pall = self.Pall
        Pall.index = pd.to_datetime(Pall.index,format='%Y-%m-%d %H:%M:%S');Pall=Pall.asfreq(freq='s');Pall.index.freq='s'
        Prate = self.Pe
        dd1 = self.deadzone1
        dd2 = self.deadzone2
        vc = self.Vn/Prate
        ts = self.tn
        Pn = self.detPn
        Result = pd.DataFrame(columns = ['AGC','Pt0','T0','Pt1','T1','Pt2','T2','Pt3','T3',
                             'Tj','Vj','detP',
                             'k1','k2','k3','kp','D','flag','Validity','Revenue'
                             ])
        ControlNo = 1
        Result.loc[ControlNo] = 0
        Agc,Pt0,T0,lasti = AGC[0],Pall[0],AGC.index[0],AGC.index[0]
        T1,T2,T3 = 0,0,0
        Pt1,Pt2,Pt3,detP,c = 0,0,0,0,0
        DeadZone1,DeadZone2 = dd1,dd2
        Vn = Prate*vc
        tn = ts
        detPn = Pn
        MAXP = 0
        MINP = Prate
        lastAgc = Pall[0]
        flag = [0,0]
        flag[1] = Agc-Pall[0]
        
        for i in AGC.index:
            if not np.isnan(AGC[i]) and not np.isnan(Pall[i]):
                if (i-lasti).total_seconds() >= ScanR:
                    '''注意不同区域定义k1，k2和k3略有不同'''
                    if abs(AGC[i]-Agc) >= VarAgc:
                        '''结算上一条指令的k值情况'''
                        
                        if T3 == 0:
                            if Agc>Pt0 :
                                '''求里程D，含折返条件'''
                                D = abs(MAXP-Pt0)+Prate*Back*flag[0]
                            else:
                                D = abs(MINP-Pt0)+Prate*Back*flag[0]
                        else:
                            D = abs(Agc-Pt0)+Prate*Back*flag[0]
                            
                        if Agc-Pt0>0:
                            if MAXP == 0:
                                print(i)
                                print('%.2f' %D)
                                D = 0
                        else:
                            if MINP == Prate:
                                print(i)
                                print('%.2f' %D)
                                D = 0
                            
                        if Pt3 == 0:
                            '''若没有扫描到T3'''
                            Pt3 = Pall[i] 
                            T3 = i
            
                        if T1 == 0:
                            '''若没有扫描到T1'''
                            Pt1 = Pall[i]
                            T1 = i
                        if T0 == 0 or T2 == 0:
                            T02 = 0
                        else:
                            T02 = (T2-T0).total_seconds()
                        if T0 == 0 or T3 == 0:
                            T03 = 0
                        else:
                            T03 = (T3-T0).total_seconds()
                        if T1 == 0 or T2 == 0:
                            T12 = 0
                        else:
                            T12 = (T2-T1).total_seconds()
                        
                        '''求k3'''
                        Tj = (T1-T0).total_seconds()
                        k3 = max([mink,maxk-Tj/tn])
                        
                        if c != 0:
                            '''求k2'''
                            detP =detP/c
                            k2 = max([mink,maxk-detP/detPn])
                        else:
                            '''若没有扫描到T3时'''
                            detP = abs(Pall[i]-Agc)
                            k2 = max([mink,maxk-detP/detPn])
                            T3 = i
                       
                        if T12 != 0:
                            '''求k1-速度V'''
                            if abs(Pt2-Pt1)>0:
                                Vj = abs((Pt2-Pt1)/T12)
                                Vj = Vj*60
                            else:
                                Vj = abs((Pt2-Pt0)/T02)
                                Vj = Vj*60
                            k1 = max([mink,maxk-Vn/Vj])
                        else:
                            T2 = i
                            Pt2 = Pall[i]
                            Vj = abs(max(0.1,D)/T03)
                            Vj = Vj*60
                            k1 = max([mink,maxk-Vn/Vj])
                        '''求kp'''
                        kp = k1*k2*k3
                        Revenue = max([0,D*(math.log(kp)+1)*Yagc])
                        Validity = 1
                        Result.loc[ControlNo] = np.array([Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3,Tj,Vj,detP,k1,k2,k3,kp,D,flag[1],Validity,Revenue])
                        '''初始化下一条指令'''
                        ControlNo += 1
                        Result.loc[ControlNo] = 0
                        lastAgc = Agc
                        Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3 = [0]*9
                        Tj,Vj,detP,c = [0]*4
                        k1,k2,k3,kp,D,Validity,Revenue = [0]*7
                        Agc,Pt0,T0 = AGC[i],Pall[i],i
                        if flag[1] * (Agc-lastAgc)<0:
                            '''折返判断，两次调节相反即折返调节'''
                            flag[0] = 1
                        else:
                            flag[0] = 0
                        flag[1] = Agc-lastAgc
                        MAXP = 0
                        MINP = Prate
                    else:
                        if Agc>Pt0:
                            '''升出力过程中的最高出力，为了计算D'''
                            if Pall[i]>MAXP:
                                MAXP = Pall[i]
                        else:
                            '''降出力过程中的最小出力，为了计算D'''
                            if Pall[i]<MINP:
                                MINP = Pall[i]
                        if T1 == 0:
                            if (Agc-Pt0)*(Pall[i]-Pt0)>0:
                                '''出响应死区'''
                                if abs(Pall[i]-Pt0)>DeadZone1:
                                    Pt1 = Pall[i]
                                    T1 = i
                        elif T2 == 0:
                            if Agc>Pt0:
                                if Pall[i]>Agc-DeadZone2:
                                    '''进入调节死区'''
                                    Pt2 = Pall[i]
                                    T2 = i
                            else:
                                if Pall[i]<Agc+DeadZone2:
                                    Pt2 = Pall[i]
                                    T2 = i
                        else:
                            '''累加响应精度偏差'''
                            T3 = i
                            detP = detP +abs(AGC[i]-Pall[i])
                            c = c+1
            
                    if i == AGC.index[-1]:
                        '''处理最后一组数据'''
                        Pt3 = Pall[i]
                        T3 = i 
                        if T0 == 0 or T2 == 0:
                            T02 = 0
                        else:
                            T02 = (T2-T0).total_seconds()
                        if T0 == 0 or T3 == 0:
                            T03 = 0
                        else:
                            T03 = (T3-T0).total_seconds()
                        if T1 == 0 or T2 == 0:
                            T12 = 0
                        else:
                            T12 = (T2-T1).total_seconds()
        
                        if T1 == 0 :
                            Pt1 = Pall[i]
                            T1 = i
                        Tj = (T1-T0).total_seconds()
                        k3 = max([mink,maxk-Tj/tn])
                        if T12 != 0:
                            if Pt2-Pt1>0:
                                Vj = abs((Pt2-Pt1)/T12)
                                Vj = Vj*60
                            else:
                                Vj = abs((Pt2-Pt0)/T02)
                                Vj = Vj*60
                            k1 = max([mink,maxk-Vn/Vj])
                        else:
                            T2 = i
                            Pt2 = Pall[i]
                            Vj = abs((Pt2-Pt0)/T02)
                            Vj = Vj*60
                            k1 = max([mink,maxk-Vn/Vj])
                        if c != 0:
                            detP = detP/c
                            k2 = max([mink,maxk-detP/Pn])
                        else:
                            k2 = mink
                        kp = k1*k2*k3
                        if Agc>Pt0:
                            D = abs(min([MAXP,Agc])-Pt0)+Prate*Back*flag[0]
                        else:
                            D = abs(max([MINP,Agc])-Pt0)+Prate*Back*flag[0]
                        Revenue = max([0,D*(math.log(kp)+1)*Yagc])
                        Validity = 1
                        Result.loc[ControlNo] = np.array([Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3,Tj,Vj,detP,k1,k2,k3,kp,D,flag[1],Validity,Revenue])
                    lasti = i
    #     lisrindex = Result[(Result.Validity>0) & (Result.k1>0)].index.tolist()#返回行的名称
    #     Result1 = Result[(Result.Validity>0)]
    #     Result2 = Result1[(Result1.k1>0)]
        meank1 = Result.k1.mean(axis=0)#对k1求平均值
        meank2 = Result.k2.mean(axis=0)
        meank3 = Result.k3.mean(axis=0)
        meank1 = min(meank1,1.5)
        meank2 = min(meank2,1.5)
        meank3 = min(meank3,1.5)
        meankp = meank1*meank2*meank3
        print(Result.kp.mean(axis=0))
        sumD = Result.D.sum()
        print('k1:%.2f \n k2:%.2f \n k3:%.2f \n kp:%.2f \n D:%.2f' %(meank1,meank2,meank3,meankp,sumD))
        Revenue = sumD*(math.log(meankp)+1)*Yagc
#         Result.to_csv(r'C:\Users\JesisW\Desktop\结果.csv',encoding='gbk',header=True,index=False)
        return meank1,meank2,meank3,meankp,sumD,Revenue

class cost_perunit():
    """
    :计算各储能电站运行时的单位MWh成本
    :参考链接D:\储能成本xlsx公式\Levelized Cost of Using Storage.xlsx
    
    :param cyc:预计循环总数
    :param cyc_day:日预计循环数
    :param Capacity:配置容量(MWh)
    :param ues_electricity_day:日用电量(MWh,理论估值)
    :param efficiency:充放电转换效率(小数形式)
    :param end_soh:电池报废截止SOH(小数形式)
    :param EMS_soc:EMS控制运行soc行程(小数形式)
    """
    def __init__(self,cyc,cyc_day,Capacity,use_electricity_day,efficiency,end_soh,EMS_soc):
        """
        :param cyc:预计循环总数
        :param cyc_day:日预计循环数
        :param Capacity:配置容量(MWh)
        :param ues_electricity_day:日用电量(MWh)
        :param efficiency:充放电转换效率(小数形式)
        :param end_soh:电池报废截止SOH(小数形式)
        :param EMS_soc:EMS控制运行soc行程(小数形式)
        """
        self.cyc = cyc
        self.cyc_day = cyc_day
        self.Capacity = Capacity
        self.use_electricity_day = use_electricity_day
        self.efficiency = efficiency
        self.end_soh = end_soh
        self.EMS_soc = EMS_soc
        self.year = self.cyc/self.cyc_day/365
        self.DOD_average = (1+self.end_soh)/2
    
    def Initial_investment_cost(self,EPC=0,installation=0,transport=0,fax=0,Battery_all=0,cooling=0,control=0,PCS=0,pack=0,module=0,container=0):
        """
        : 初始投资成本核算,单位元,请将万元等单位转换为元
        : EPC是总承包成本，若给出EPC则不用给出其他的参数
        : battery_all是电池部分成本，若给出battery_all则不用给出其他电池成本
        
        :param EPC:总承包成本，包含所有成本，如电池、安装、运输、税费、制冷、控制、PCS、集装箱、基建等
        :param installation:安装成本
        :param transport:运输成本
        :param fax:税费
        :param battery_all:电池整体成本，包含制冷，控制，PCS成本，模组，集装箱等
        :param cooling:制冷
        :param control:控制
        :param PCS:PCS成本
        :param pack:簇
        :param module:模组/电池
        :param container:集装箱
        
        :return initial_investment_cost:初始投资成本
        """
        if EPC != 0:
            self.initial_investment_cost = EPC
#             print('投资资金为:%d' %(self.initial_investment_cost))
            return 0
        else:
            self.initial_investment_cost = installation+transport+fax
            if Battery_all !=0:
                self.Battery_all = Battery_all
                self.initial_investment_cost += Battery_all
#                 print('投资资金为:%d' %self.initial_investment_cost)
                return 0
            else:
                self.Battery_all = cooling+control+PCS+pack+module+container
                self.initial_investment_cost = self.initial_investment_cost+cooling+control+PCS+pack+module+container
#                 print('投资资金为:%d' %self.initial_investment_cost)
                if self.initial_investment_cost == 0:
                    print('投资资金未知，无法计算')
                    return -1
                return 0
    def Operation_cost(self,All=0,maintain=0,insurance=0,use_electricity=0,charge_cost=0,auxiliary=0,management=0,monitoring=0,recycl=0):
        """
        : 运行成本核算,使用期限内的全部运行成本
        : 用电成本包含充电成本和辅助用电成本
        
        :param All:全部运行成本,可不配其他成本
        :param maintain:运行维护成本/元
        :param insurance:保险/元
        :param use_electricity:用电成本/元
        :param charge_cost:充电成本/元
        :param auxiliary:辅助用电成本/元
        :param management:管理成本/元
        :param monitoring:监控成本/元
        :param recycl:回收成本(一次成本)
        
        :return operation_cost:运行成本
        """
        if All != 0:
            self.operation_cost=All
            print('运行成本:%d' % self.operation_cost)
            return
        else:
            if maintain == 0:
                # 如果没给运行维护成本，则根据百分比计算
                maintain = self.initial_investment_cost*0.002*self.year
            if insurance ==0:
#                 N = input('请选择是否有保险，有Y，没有N')
                N = 'Y'
                if 'Y' in N:
                    insurance = self.initial_investment_cost*0.015*self.year
                else:
                    insurance = 0
            self.operation_cost = maintain+insurance
            
            if management == 0:
                management = self.initial_investment_cost*0.0015*self.year
            self.operation_cost += management
            
            if monitoring == 0:
                monitoring = self.initial_investment_cost*0.0015*self.year
            self.operation_cost += monitoring
            
            if use_electricity !=0:
                self.operation_cost += use_electricity
#                 print('运行成本:%d' % self.operation_cost)
                return
            else:
                charge_cost = self.cyc*self.Capacity*0.15*200
                auxiliary = 5.31/15*self.Capacity*365*self.year*200
                self.operation_cost = self.operation_cost+charge_cost+auxiliary+recycl
#                 print('运行成本:%d' % self.operation_cost)
                return
    def Replacement_cost(self,year_insure=0):
        """
        : 若在质保年限中一次电源无法满足时需要更换电池整体
        
        :param year_insure: 承诺的使用年限
        
        :return repalcement_cost:替换成本
        """
        if year_insure == 0:
#             print('无需更换')
            return
        else:
            change_times = year_insure//(int(self.year)+1)+1
            for i in range(1,change_times):
                self.replacement_cost += self.Battery_all*(0.75**change_times)
    def Unit_cost(self):
        self.per_init_cost = self.initial_investment_cost/self.Capacity
        self.per_operat_cost_year = self.operation_cost/self.Capacity/self.year
        self.unit_cost = (self.per_init_cost+self.per_operat_cost_year*self.year)/(self.cyc*self.efficiency*self.DOD_average*self.EMS_soc)
#         print('每MWh的放电成本:%.2f' % self.unit_cost)
        return self.unit_cost

class Heat_analyse():
    '''
    :无需初始化，直接调用Heat_distribution函数
    '''
    def __init__(self):
        return

    def Heat_distribution(self,Current,Current_Max,rating,time=None,Threshold_rate=0.8):
        '''
        :该函数用来求取热相关分析
        :本部分主要统计连续最大功率输出的时长分布
        :param Current:电流数据
        :param time:对应时间
        :param Current_Max:最大电流,若为站电流:给出站最大电流;若为堆电流:给出堆最大电流;若为包电流:给出包最大电流;其他类比
        :param rating:等级,若为站:则是1;若为箱:则是2;若为堆:则为3;若为簇:则是4;若为包:则是5;
        :param threshold:认定电流阈值(小数),超过该值则认为是满功率
        
        :return data:电流分布统计数据
        '''
        if time is not None:
            time = pd.to_datetime(time,format ='%Y-%m-%d %H:%M:%S')
        else:
            time = pd.date_range(start='00:00:00',periods=len(Current),freq='1S')
        rating_map = {'1':'站','2':'箱','3':'堆','4':'簇','5':'包'}
        print('--------------选择对%s进行分析------------' %rating_map[str(rating)])
        Current.index = time
        Threshold = Current_Max*Threshold_rate
        print('认为超过%.2fA的电流即为满功率输出,对该阈值进行分析' %Threshold)
        count = -1
        Reset = 0
        data = pd.DataFrame(columns=['起始时间','结束时间','时长'])
        for i in time:
            if abs(Current[i])>Threshold:
                if Reset == 0 :
                    i_start = i
                    count += 1
                    Reset = 1
            else:
                if Reset != 0:
                    i_end = i
                    Reset = 0
                    data.loc[count,:] = [i_start,i_end,(i_end-i_start).seconds]
        return data