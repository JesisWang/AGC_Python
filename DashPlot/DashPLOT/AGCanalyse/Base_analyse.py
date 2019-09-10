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
    运行得到AGC相关分析:
    电站名称：新丰，云河，海丰，河源，鲤鱼江，恒运，宣化，准大，兴和，上都，平朔，同达
    类下变量说明：
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
        Pe = [300,300,1000,600,300,300,330,300,300,600,300,300] # 机组额定功率
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
            self.Vn = self.Pe*0.01903
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
        输入参数：
        detAgc : 区分AGC之间的阈值
        输出参数:
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
    
    def BATstrength(self,initial_SOC=50,detAgc=2,scanrate=1):
        '''
        储能电站的强度分析曲线，若没有储能数据，则无法分析
        包含储能的运行成本分析
        输入参数:
        initial_SOC:初始SOC
        detAgc:区分AGC的大小
        scanrate:扫描频率
        输出参数:
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
        Cost = max([Eqv_cycplus,-Eqv_cycminus])/5000*0.4*1000*1000*Ee
        elecFee = (abs(MinusE_Pdg) - PlusE_Pdg)*0.25*1000
        return BatResult,Cost,elecFee,Eqv_cycminus,Eqv_cycplus
    
    def PDGstrength(self,detAgc=2,ft_time=10):
        '''
        输入参数:
        detAgc: 区分AGC的阈值
        ft_time: 反调持续最小时间
        输出参数:
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
        return Result,Op1,Op2,Op3,Op4,S,M,K
    
class MX(operation_analyse):
    '''
     计算蒙西的Kp值和收益
     stationname:电站名称，需要给出
     '''
    def Kp_Revenue(self,ScanR=5,ADJK1=2.1,minT=30,maxV=5,VarAgc=2,VarPdg=0.01,K1max=4.2,Back=0.05,mink=0.1,maxk=2):
        '''
        该文档是用来计算蒙西电网K-D-Revenue的函数
        各参数含义如下：
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
        Back:折返系数，如0.05
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
            AGC.index = pd.to_datetime(AGC.index,format='%Y-%m-%d %H:%M:%S');AGC.asfreq(freq='s');AGC.index.freq='s'
            Pall = self.Pall
            Pall.index = pd.to_datetime(Pall.index,format='%Y-%m-%d %H:%M:%S');Pall.asfreq(freq='s');Pall.index.freq='s'
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
            for i in AGC.index:
                if AGC[i] is not None:
                    if (i-ilast).total_seconds() >= Scanrate:
                        if abs(AGC[i]-Agc) >= VarAgc:
                            '''Agc变化，结算上一条指令 的各项k值'''
                            Pt3 = Pall[ilast]
                            T3 = ilast
                            if T1 == 0:
                                '''若没有扫描到T1'''
                                Pt1 = Pall[ilast]
                                T1 = ilast
                            
                            if T2 == 0:
                                '''若没有扫描到T2'''
                                Pt2 = Pall[ilast]
                                T2 = ilast
                            
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
                            
                            if T03 <= minT or Agc-Pt0 <= Prate*VarPdg or Vj>maxV*Vn:
                                '''新丰有效指令判断:规则1：指令时长>30s，规则2:Agc与初始机组差值>0.01*Prate,规则3:速度V<5*标准速率，否则记为无效
                                '''
                                Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3 = [0]*9
                                Tj,Vj,detP = [0]*3
                                k1,k2,k3,kp,D,flag[1],Validity = [0]*7
                            else:
                                '''求k3'''
                                Tj = (T1-T0).total_seconds()
                                k3 = max([mink,maxk-Tj/tn])
                                '''求k1'''
                                k1 = Vj/Vn
                                if k1 > K1max :
                                    k1 = mink
                                
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
                            '''初始化下一条指令'''
                            Result.loc[ControlNo] = 0
                            Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3 = [0]*9
                            Tj,Vj,detP = [0]*3
                            k1,k2,k3,kp,D,Validity = [0]*6
                            Agc,Pt0,T0 = AGC[i],Pall[i],i
                            flag[0] = flag[1]
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
                                detP = detP+abs(Pall[i]-Agc)*(ilast-i).total_seconds()
                
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
                                Result.loc[ControlNo].pop()
                            else:
                                Tj = (T1-T0).total_seconds()
                                k3 = max([mink,maxk-Tj/tn])
                                
                                k1 = Vj/Vn
                                if k1 > K1max:
                                    k1 = mink
                                
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
        Revenue = meankp*sumD*0.02
        return meank1,meank2,meank3,meankp,sumD,Revenue

class GD(operation_analyse):
    '''
     计算广东的Kp值和收益
     stationname:电站名称，需要给出
    '''
    def Kp_Revenue(self,ScanR=1,VarAgc=0.005,maxk23=1,maxk1=5,TminCon=20,TminVt=30,TminTa=20,TmaxTa=40,TminTR=4,Yagc=12):
        '''
        该文档是用来计算广东区电站K-D-Revenue的函数
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
        AGC.index = pd.to_datetime(AGC.index,format='%Y-%m-%d %H:%M:%S');AGC.asfreq(freq='s');AGC.index.freq='s'
        
        Pall = self.Pall
        Pall.index = pd.to_datetime(Pall.index,format='%Y-%m-%d %H:%M:%S');Pall.asfreq(freq='s');Pall.index.freq='s'
        
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
        ControlNo = 1
        Result.loc[ControlNo] = 0
        Agc,Pt0,T0,lasti = AGC[0],Pall[0],0,AGC.index[0]
        T1,T2,T3 = 0,0,0
        k1,k2,k3 = 0,0,0
        Pt1,Pt2,Pt3,detP = 0,0,0,0
        Pend,Pvst,Tvst,Pvend,Tvend = 0,0,0,0,0
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
        k1set,k2set,k3set = -1,-1,-1
        CountT = 0
        Psd = max(0.01*Prate,5)
        Pt1_temp,T1_temp = 0,0
        V_all = []
        for i in AGC.index:
            if AGC[i] is not None:
                if (i-lasti).total_seconds() >= ScanR:
                    if abs(AGC[i]-Agc) >= detAgc:
                        '''结算上一条Agc指令的k值'''
                        if T2 == 0 or T3 == 0:
                            T = 0
                        else:
                            T = (T3-T2).total_seconds()
                        if (AGC[i]-Pt0)*flag[0]>0 and (AGC[i]-Agc)*flag[0]>0 and T<TminCon:
                            '''合并条件:升出力方向相同；调节方向相同；进入死区时间不足20s，则合并，否则结算'''
                            if Tvst == 0 or Tvend == 0:
                                Tv = 0
                            else:
                                Tv = (Tvend-Tvst).total_seconds()
                            if ControlNo == 1:
                                Result.loc[ControlNo] = 0
                                ControlNo = ControlNo+1
                                Result.loc[ControlNo] = 0
                                Agc = AGC[i]
                                Pt0 = Pall[i]
                                T0 = i
                                Psend = 0.7*Agc+0.3*Pt0
                                flag[1] = Agc-Pt0
                            else:
                                Agc = AGC[i]
                                Pt2 = 0
                                T2 = 0
                                T3 = 0
                                detP = 0
                                Psend = 0.7*Agc+0.3*Pall[i]
                                if Tvend == 0:
                                    Pvst,Tvst,Pvend,Tvend = 0,0,0,0
                                else:
                                    if Pvend-Pvst >=DeadZone2 and Tv>TminTR:
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
                                Result.loc[ControlNo] = 0
                                ControlNo = ControlNo+1
                                Result.loc[ControlNo] = 0
                                Agc = AGC[i]
                                Pt0 = Pall[i]
                                T0 = i
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
                                
                                if V1[0] == 0:
                                    if Tvst == 0 or Tvend == 0:
                                        Vj = k1set
                                    else:
                                        if Pvend-Pvst >=DeadZone2 and Tv>TminTR:
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
                                        if Pvend-Pvst >=DeadZone2 and Tv>TminTR:
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
                                Psend = 0.7*Agc + 0.3*Pt0
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
                                if Pvend-Pvst >=DeadZone2 and Tv>TminTR:
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
                                if Pvend-Pvst >=DeadZone2 and Tv>TminTR:
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
                        Result.loc[ControlNo] = np.array([Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3,Tj,Vj,detP,k1,k2,k3,kp,Pend,D,flag[0],Pmax,Pvst,Tvst,Pvend,Tvend,Validity,Revenue])
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
        Revenue = sumD*meankp*Yagc
#         Result.to_csv(r'C:\Users\JesisW\Desktop\结果.csv',encoding='gbk',header=True,index=False)
        return meank1,meank2,meank3,meankp,sumD,Revenue
    def Kp_Revenue_2018(self,ScanR=1,VarAgc=0.002,maxk23=1,maxk1=5,TminCon=15,TminVt=30,TminTa=20,TmaxTa=40,TminTR=4,Yagc=12):
        '''
        该文档是用来计算广东区电站K-D-Revenue的函数
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
        AGC.index = pd.to_datetime(AGC.index,format='%Y-%m-%d %H:%M:%S');AGC.asfreq(freq='s');AGC.index.freq='s'
        
        Pall = self.Pall
        Pall.index = pd.to_datetime(Pall.index,format='%Y-%m-%d %H:%M:%S');Pall.asfreq(freq='s');Pall.index.freq='s'
        
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
        PTi = max(0.02*Prate,20)
        Pt1_temp,T1_temp = 0,0
        Tend_v,Pend_v = T0+int(abs(Agc-Pt0)*60/Vn+Scanrate+1),0
        for i in AGC.index:
            if AGC[i] is not None:
                if (i-lasti).total_seconds() >= Scanrate:
                    if abs(AGC[i]-Agc) >= detAgc:
                        '''结算上一条Agc指令的k值'''
                        if T2 == 0 or T3 == 0:
                            T = 0
                        else:
                            T = (T3-T2).total_seconds()
                        if (AGC[i]-Pt0)*flag[0]>0 and (AGC[i]-Agc)*flag[0]>0 and T<=TminCon:
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
        
class HB(operation_analyse):
    '''
     计算华北的Kp值和收益
     stationname:电站名称，需要给出
    '''
    def Kp_Revenue(self,ScanR=3,VarAgc=5,Back=0.005,mink=0.1,maxk=2,Yagc=5.2):

        '''
        该文档是用来计算华北区电站K-D-Revenue的函数
        各参数含义如下：
        AGC:电网下达的AGC功率指令值，功率单位MW，时间间隔1秒
        Pall:联合功率值，功率单位MW，时间间隔为1秒
        RowNum:为计算样本采样点数，时间间隔为1秒，若相邻数据间的间隔不为1秒，请处理源数据，如一天的样本为86400个(秒)
        Prate:机组的额定功率，单位MW，如300MW
        dd1:响应死区系数
        dd2:调节死区系数
        vc:机组额定速率系数，如0.015倍的机组额定功率
        ts:标准响应时间，单位秒，如60s
        Pn:标准响应偏差系数，如0.008的机组额定功率
        ScanR:扫描频率，单位秒，如3秒
        VarAgc:相邻Agc的区分界限，如相差5MW及以上
        Back:折返系数，如0.05
        mink:k1，k2，k3的最小取值，一般为0.1
        maxk:k2,k3的最大取值，一般为2
        Yagc:单位补偿金额
            参数返回：
        1——k1
        2——k2
        3——k3
        4——Kp
        5——里程D
        6——收益Revenue
        '''
        AGC = self.Agc
        AGC.index = pd.to_datetime(AGC.index,format='%Y-%m-%d %H:%M:%S');AGC.asfreq(freq='s');AGC.index.freq='s'
        Pall = self.Pall
        Pall.index = pd.to_datetime(Pall.index,format='%Y-%m-%d %H:%M:%S');Pall.asfreq(freq='s');Pall.index.freq='s'
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
            if AGC[i] is not None:
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
                                print('%.2f' %D)
                                D = 0
                        else:
                            if MINP == Prate:
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
                        Revenue = max([0,D*(math.log(kp+1))*Yagc])
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
                        Revenue = max([0,D*(math.log(kp+1))*Yagc])
                        Validity = 1
                        Result.loc[ControlNo] = np.array([Agc,Pt0,T0,Pt1,T1,Pt2,T2,Pt3,T3,Tj,Vj,detP,k1,k2,k3,kp,D,flag[1],Validity,Revenue])
                    lasti = i
    #     lisrindex = Result[(Result.Validity>0) & (Result.k1>0)].index.tolist()#返回行的名称
    #     Result1 = Result[(Result.Validity>0)]
    #     Result2 = Result1[(Result1.k1>0)]
        meank1 = Result.k1.mean(axis=0)#对k1求平均值
        meank2 = Result.k2.mean(axis=0)
        meank3 = Result.k3.mean(axis=0)
        meankp = meank1*meank2*meank3
        print(Result.kp.mean(axis=0))
        sumD = Result.D.sum()
        Revenue = sumD*(math.log(meankp)+1)*Yagc
        return meank1,meank2,meank3,meankp,sumD,Revenue
