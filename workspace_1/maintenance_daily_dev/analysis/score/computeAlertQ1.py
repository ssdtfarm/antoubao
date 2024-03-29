#!/usr/bin/python
#coding=utf-8
import numpy as np
from scipy import interpolate
import time
import hashlib
from atbtools.header import *
from atbtools.mysqlTools import *
from atbtools.computeTools import *

#线性拟合结果
def linearfit(x,y):
    N = len(x)
    sx,sy,sxx,syy,sxy = 0,0,0,0,0
    for i in range(N):
        sx += x[i]
        sy += y[i]
        sxx += x[i]*x[i]
        syy += y[i]*y[i]
        sxy += x[i]*y[i]
    a = (sy*sx/N - sxy)/(sx*sx/N - sxx)
    b = (sy - a*sx)/N
    if (sxx-sx*sx/N)*(syy-sy*sy/N) == 0:
        r = 0
    else:
        r = abs(sy*sx/N - sxy)/math.sqrt((sxx-sx*sx/N)*(syy-sy*sy/N))
    return a,b,r
    
#B样条插值(7周数据)的预测值误差
def warning1(_list):
    if None in _list or _list[6] == 0:
        return "f1"
    else:
        y = _list[0:6]
        x = np.array(range(0,6))
        x_new = np.array(range(0,7))
    #     f_linear = interpolate.interp1d(y,x)
        tck = interpolate.splrep(x,y) #B样条插值函数
        x_bspline = interpolate.splev(x_new,tck) #B样条插值结果
        value = abs(float(x_bspline[6]/_list[6]) - 1)
        if value >= 0.5:
            return "w1"
        else:
            return ""
    
#线性拟合(4周数据)的预测值误差
def warning2(_list):
    if None in _list:
        return "f2"
    else:
        r = linearfit([1,2,3,4],_list)[2]
        if (abs(r) > 0.85):
            return "w2"
        else:
            return ""

#本周和上一周的差的绝对值
def warning3(_list):
    if None in _list:
        return"f3"
    else:
        if abs(_list[0] - _list[1]) > 10:
            return "w3"
        else:
            return ""
    
#是否在拟定最大值和最小值之间（包含等于）
def warning4(_value, _minn, _maxx):
    if None == _value:
        return "f4"
    else:
        if (_value < _minn) or (_value > _maxx):
            return "w4"
        else:
            return ""
        
#是否在拟定最大值和最小值之间（包含等于）
def warning5(_value, _minn, _maxx):
    if None == _value:
        return "f5"
    else:
        if (_value < _minn) or (_value > _maxx):
            return "w5"
        else:
            return ""
        
#是否在拟定最大值和最小值之间（包含等于）
def warning6(_list):
    if _list[-1] != None and _list[-3] != None:
        numerator = float(abs(_list[-1] - _list[-3]))
    else:
        return "f6"
    denominator = 0.0
    count = 0
    for i in range(7):
        if _list[i + 2] != None and _list[i] != None:
            denominator += abs(_list[i + 2] - _list[i])
            count += 1
    if count == 0 or denominator == 0:
        return "f6"
    else:
        denominator /= count
    value = numerator / denominator
    if value <= 1.3 or value >= 0.7:
        return "w6"
    else:
        return ""

if __name__ == '__main__':
    _start_time = time.time()
    
    #获取连接
    conn_dev=MySQLdb.connect(host=DEVHOST, user=USERNAME, passwd=PASSWORD, db=DB, port=PORT) 
    conn_ddpt=MySQLdb.connect(host=DDPT_DATAHOST, user=USERNAME, passwd=PASSWORD, db=DB, port=PORT) 
    conn_db=MySQLdb.connect(host=DBHOST, user=USERNAME, passwd=PASSWORD, db=DB, port=PORT) 
    cur_dev=getCursors(conn_dev)
    cur_ddpt=getCursors(conn_ddpt)
    cur_db = getCursors(conn_db)
    initializeCursors(cur_dev, cur_ddpt, cur_db)
    
    SRCDB_R = "platform_alert_info_R"
    SRCDB_E3 = "E3_quantitative_score"
    SRCDB_SIGMA3 = "K_statis_3sigma"
    SRCDB_Y = "total_status"
   
    cur_dev.execute("DELETE FROM " + SRCDB_R)
    conn_dev.commit()
 
    del_list = ["date", "id", "platform_id", "platform_name", "provision_of_risk_num", "cap_background"]
    field_list = getAllColumnsFromTable(cur_ddpt, SRCDB_E3, del_list = del_list, merge_list = None)
    field_number = len(field_list)
    w4_field_list = ["turnover_registered", "weekly_ave_bid_close_time", "weekly_ratio_new_old", "not_returned_yet", "outstanding_loan"]
    w4_field_number = len(w4_field_list)
    
    date_list = getDifferentFieldlist(SRCDB_E3, cur_ddpt, "date")
    date_number = len(date_list)
    platform_name_list = getDifferentFieldlist(SRCDB_E3, cur_ddpt, "platform_name")
    platform_name_number = len(platform_name_list)
    
    #获取所有数据
    value_dict = {}
    for platform_name in platform_name_list:
        value_dict[platform_name] = {}
        for field in field_list:
            value_dict[platform_name][field] = [None] * date_number
    stringSQL = "SELECT `platform_name`, `date`, `" + "`, `".join(field_list) + "` FROM " + SRCDB_E3
    print "正在从数据库传输数据回本地..."
    cur_ddpt.execute(stringSQL)
    rows = cur_ddpt.fetchall()
    for row in rows:
        platform_name = row[0]
        date = row[1]
        value_list = row[2:]
        date_index = date_list.index(date)
        for i in range(field_number):
            value_dict[platform_name][field_list[i]][date_index] = value_list[i]

    #获取3sigma数据
    sigma3_dict_high = {}
    sigma3_dict_low = {}
    for field in w4_field_list:
        sigma3_dict_high[field] = [None] * date_number
        sigma3_dict_low[field] = [None] * date_number
    stringSQL = "SELECT `type`, `date`, `" + "`, `".join(w4_field_list) + "` FROM " + SRCDB_SIGMA3
    cur_ddpt.execute(stringSQL)
    rows = cur_ddpt.fetchall()
    for row in rows:
        _type = row[0]
        date = row[1]
        value_list = row[2:]
        date_index = date_list.index(date)
        for i in range(w4_field_number):
            if _type == "h":
                sigma3_dict_high[w4_field_list[i]][date_index] = value_list[i]
            else:
                sigma3_dict_low[w4_field_list[i]][date_index] = value_list[i]
    
    #获得所有平台的status属性
    status_dict = {}
    stringSQL = "SELECT A.platform_name, A.status FROM total_status AS A,(SELECT `platform_name`, MAX(`date`) AS `date` FROM total_status GROUP BY `platform_name`) AS B WHERE A.platform_name = B.platform_name AND A.`date` = B.`date`"
    ret = cur_db.execute(stringSQL)
    rows = cur_db.fetchall()
    for row in rows:
        platform_name = row[0]
        status = row[1]
        status_dict[platform_name] = status
    #开始计算预警
    for platform_name in value_dict:
        print platform_name
        platform_id = hashlib.md5(platform_name).hexdigest()[0:10]
        for i in range(0,date_number):
            date = date_list[i]
            v = {}.fromkeys(field_list, "")
            
            #w1，最近7周B样条插值
            if i >= 6:
                for field in field_list:
                    last7week_list = value_dict[platform_name][field][i-6:i+1]
                    v[field] += warning1(last7week_list)
                    
            #w2，最近4周线性拟合
            if i >= 3:
                for field in field_list:
                    last4week_list = value_dict[platform_name][field][i-3:i+1]
                    v[field] += warning2(last4week_list)
                    
            #w3，相邻两周数据差
            if i >= 1:
                for field in field_list:
                    last2week_list = value_dict[platform_name][field][i-1:i+1]
                    v[field] += warning3(last2week_list)
            
            #w4，特殊指标是否在3sigma内
            for field in w4_field_list:
                this_date_value = value_dict[platform_name][field][i]
                v[field] += warning4(this_date_value, sigma3_dict_low[field][i], sigma3_dict_high[field][i])
                        
            #w5，指标是否在指定阈值外
            for field in field_list:
                this_date_value = value_dict[platform_name][field][i]
                v[field] += warning5(this_date_value, -10000, 10000)
            
            if i >= 8:
                for field in field_list:
#                     print field
                    last9week_list = value_dict[platform_name][field][i-8:i+1]
                    v[field] += warning6(last9week_list)
            
            #插入数据
            field_list_new = ["platform_name", "platform_id", "date"] + field_list         
            value_list = [platform_name, platform_id, date]
            for field in field_list:
                value_list.append(v[field])
            if platform_name in status_dict:
                field_list_new += ['status']
                value_list += [str(status_dict[platform_name])]
            stringSQL = "INSERT INTO " + SRCDB_R + "(`" + "`,`".join(field_list_new) + "`) VALUES('" + "','".join(value_list) + "')"
#             print stringSQL
            cur_dev.execute(stringSQL)
            conn_dev.commit()
    closeCursors(cur_dev, cur_ddpt, cur_db)
    closeConns(conn_dev, conn_ddpt, conn_db)  
    _end_time = time.time()
    print "The whole program costs " + str(_end_time - _start_time) + " seconds." 