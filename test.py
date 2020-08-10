from pprint import pprint

import ccxt
import pymongo
import time
from util import config


config.loads('./.config.json')
# 定义交易所
okex = ccxt.okex({
    'apiKey': config.apiKey,
    'secret': config.secret,
    'password': config.password
})

# 定义mongodb
myClient = pymongo.MongoClient("mongodb://localhost:27017")
mydb = myClient["OKEX"]
mycol = mydb["EOSUSDT"]
mycol.drop()

# 定义下单参数
order_symbol = 'EOS/USDT'
order_type = 'limit'
order_side = 'sell'
order_amount = 0.1  # 单笔交易 = order_amout * order_price

# 获取EOS最新价格

eos_last = okex.fetch_ticker(order_symbol)['last']
print("EOS 最新价格", eos_last)

order_price = eos_last - 0.01  # 添加手续费 0.1%

# order_price = eos_last * 1.00015


# 需求： 下num个订单， 循环监控订单状态， 如果买单成交， 则下一个卖单， 如果卖单成交， 就下一个买单
num = 3

while num > 0:

    eos_balance = okex.fetch_balance()['free']['USDT']


    if eos_balance >= 1:

        take_order = okex.create_order(
            order_symbol, order_type, order_side, order_amount, order_price)

        pprint(take_order)

        order_price -= 0.01

        eos_balance = okex.fetch_balance()['free']['USDT']

        print("当前balance", eos_balance)
        print("*" * 20)
    else:
        print("余额不足, 小于 1.0: ", eos_balance)

    num -= 1
    time.sleep(1)

# aa = okex.fetch_balance()['EOS']['free']

online_order = okex.fetch_open_orders(order_symbol)

# pprint(online_order)

for m in online_order:
    # 存储订单信息
    mydict = {"单价": m['price'],
              "订单号": m['id'], "方向": m['side']}
    x = mycol.insert_one(mydict)
print("数据库插入完成")

exit()

while 1:
    for y in mycol.find():
        takeorder_id = y['订单号']
        takeorder_side = y['方向']
        takeorder_price = y['单价']
        print("*" * 10)

        # 获取 eos 最新价格
        eos_last = okex.fetch_ticker(order_symbol)['last']
        print("eos 最新价格", eos_last)

        print("orderid", takeorder_id)

        # 查询订单状态
        order_status = okex.fetch_order_status(takeorder_id, order_symbol)
        print(order_status)

        # 如果买单成交
        if order_status == "canceled" and takeorder_side == "buy":

            # 定义卖单价格
            sell_side = "sell"

            sell_price = takeorder_price + 0.5  # shouxufei

            # 下卖单
            take_sell_order = okex.create_order(
                order_symbol, order_type, sell_side, order_amount, sell_price)

            # 卖单信息存入数据库
            print("开始写入数据库")
            mydict = {
                "单价": take_sell_order['price'], "订单号": take_sell_order['id'], "方向": take_sell_order['side']}

            mycol.insert_one(mydict)

            # 删除已完成订单
            myquery = {"订单号": takeorder_id}
            mycol.delete_one(myquery)
            print("已删除完成订单， 订单号为:", takeorder_id)

            time.sleep(3)

        elif order_status == "canceled" and takeorder_side == "sell":
            buy_side = "buy"
            buy_price = eos_last - 0.08

            take_buy_order = okex.create_order(
                order_symbol, order_type, buy_side, order_amount, buy_price)

            # 卖单信息存入数据库
            mydict = {
                "单价": take_buy_order['price'], "订单号": take_buy_order['id'], "方向": take_buy_order['side']}

            mycol.insert_one(mydict)

            # 删除已完成订单
            myquery = {"订单号": takeorder_id}
            mycol.delete_one(myquery)
            print("已删除完成订单， 订单号为:", takeorder_id)

            time.sleep(3)
        else:
            print("订单处于其他状态")
            time.sleep(1)
