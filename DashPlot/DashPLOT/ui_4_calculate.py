'''
Created on 2019年11月7日

@author: JesisW
'''
import tkinter as tk
import pandas as pd

class ui_4_fig_sim():
    def operation_analyse(self,Agc,Pdg,Pbat,time,discharge1,discharge2,charge1,charge2):
        Pe = 1000
        BatPe = 30
        BatCapacity = 15
        if time is not None:
            time = pd.to_datetime(time,format='%Y-%m-%d %H:%M:%S')
        else:
            time = pd.date_range(start='00:00:00',periods=len(time),freq='1S')
        BAT = Pbat
        PDG = Pdg
        Ee = BatCapacity
        AGC = Agc
        indexn = time
        Length = len(AGC)
        BatResult = pd.DataFrame(columns=['Agc','正向调节功率','负向调节功率','等效2C放电时长','等效2C充电时长','DOD','累积放电深度','SOC','累积未跟踪数'])
        ctl,Pz,Pf,DOD,Sd,SOC = 0,0,0,0,0,0
        BatResult.loc[ctl] = 0
        Agc,SOC0,i0,ia =AGC[0],0,indexn[0],0
        n,z = 0,0
        for i in range(0,Length-1):
            if (indexn[i]-i0).total_seconds()>=1:
                del_t = (indexn[i]-i0).total_seconds()
                if abs(AGC[i]-Agc)>2:
                    DOD = DOD/Ee*100
                    if ctl == 0:
                        Sd = DOD
                        SOC = SOC0 - DOD
                    else:
                        Sd = Sd+DOD
                        SOC = SOC - DOD
                    BatResult.iloc[ctl,0:10] = [Agc,Pz,Pf,Pz/BatPe,Pf/BatPe,DOD,Sd,SOC,n]
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
        return len(BatResult.DOD[(BatResult.DOD!=0)]),n
    
    def simulation(self):
        global e,window
        path = e.get()
        path = path.replace("\\","/")
        Aim_names_Chinese = '海丰'
        index_loc = 'GD'
        try:
            DF = pd.read_csv(path,encoding ='gbk',header=0)
            DF.index = DF['时间']
            DF.index = pd.to_datetime(DF.index,format='%Y-%m-%d %H:%M:%S')
            DF['时间'] = pd.to_datetime(DF['时间'],format='%Y-%m-%d %H:%M:%S')
            Bat = DF['2#联合出力']-DF['2#机组出力']
            Agc = DF['2#AGC指令']
            Pdg = DF['2#机组出力']
            discharge1 = DF['储能A段可放功率']
            discharge2 = DF['储能B段可放功率']
            charge1 = DF['储能A段可充功率']
            charge2 = DF['储能B段可充功率']
            time = pd.to_datetime(DF.index,format='%Y-%m-%d %H:%M:%S')
            time.columns = ['time']
            num1,num2 = self.operation_analyse(Agc,Pdg,Bat,time,discharge1,discharge2,charge1,charge2)
            I3 = tk.Label(window,
                     text='储能跟踪次数为:{0},储能由于电量未能跟踪次数为:{1}'.format(num1,num2),
                     bg = 'white',
                     font = ('宋体',12),
                     width=50,height=1)
            I3.pack()
        except :
            I3 = tk.Label(window,
                     text='文件存在问题,请参照示例后重新输入',
                     bg = 'white',
                     font = ('宋体',12),
                     width=50,height=1)
            I3.pack()
        return
    def prompt_box(self):
        global window
        I2 = tk.Label(window,
                     text='正在计算,请等待.....',
                     bg = 'white',
                     font = ('宋体',12),
                     width=30,height=1)
        I2.pack()
        self.simulation()
    def fig(self):
        # 窗口属性
        global e,window
        window = tk.Tk()
        window.title('用于计算储能跟踪')
        window.geometry('800x200')
        vari = tk.StringVar()
        I = tk.Label(window,
                     text='储能跟踪计数器',
                     bg = 'white',
                     font = ('宋体',12),
                     width=15,height=1)
        I.pack()
        I1 = tk.Label(window,
                     text=r'请输入文件全路径：如E:\1伪D盘\海丰INFINT介绍\第一次储能策略改动\2019-11-05.csv',
                     bg = 'white',
                     font = ('宋体',12),
                     width=80,height=2)# width,heigth是百分比
        I1.pack()
        e = tk.Entry(window,
                     width=80)
        e.pack()
        b = tk.Button(window,
                      text = '开始执行',
                      width=15,height=1,
                      command=self.prompt_box)
        b.pack()
        
        window.mainloop() # 让窗口活动起来
    

def main():
    f = ui_4_fig_sim()
    f.fig()
    return

if __name__ == '__main__':
    main()