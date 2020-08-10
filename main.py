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
db = myClient["OKEX"]
collection = db["EOS/USDT"]
collection.drop()

# 定义下单参数
# buy

fee_rate = 0.0015

order_symbol = 'EOS/USDT'
order_type = 'limit'
order_side = 'buy'
order_amount = 0.10016

# 获取EOS最新价格

eos_last = okex.fetch_ticker(order_symbol)['last']

print("EOS 最新价格", eos_last)

order_price = eos_last * order_amount * 10 - 0.005

# fee_rate = okex.calculate_fee(order_symbol,order_type,order_side,order_amount,order_price,'taker')['rate']
# set by exchange
order_fee = order_amount * fee_rate

usdt_balance = okex.fetch_free_balance()['USDT']

final_order = order_price * order_amount

num = 2
while num > 0 and usdt_balance > final_order:
    take_order = okex.create_order(
        order_symbol, order_type, order_side, order_amount, order_price)

    post = {"单价": order_price,
            "订单号": take_order['id'],
            "方向": take_order['side']}
    x = collection.insert_one(post)
    print("数据库插入完成")

    eos_last = okex.fetch_ticker(order_symbol)['last']
    order_price = eos_last * order_amount * 10 - 0.05
    final_order = order_price * order_amount
    usdt_balance = okex.fetch_balance()['free']['USDT']

    num -= 1
    time.sleep(1)

# online_order = okex.fetch_open_orders(order_symbol)

# for order in online_order:
#     # 存储订单信息
#     post = {"单价": order['price'],
#             "订单号": order['id'],
#             "方向": order['side'],
#             "手续费": order_fee}
#     x = collection.insert_one(post)

# print("数据库插入完成")

while 1:
    for i in collection.find():
        takeorder_id = i['订单号']
        takeorder_side = i['方向']
        takeorder_price = i['单价']
        takeorder_fee = order_fee
        print("*" * 10)

        # 获取 eos 最新价格
        eos_last = okex.fetch_ticker(order_symbol)['last']
        print("eos 最新价格", eos_last)

        print("orderid", takeorder_id)

        # 查询订单状态
        order_status = okex.fetch_order_status(takeorder_id, order_symbol)
        print(order_status)

        # 如果买单成交
        if order_status == "closed" and takeorder_side == "buy":

            # 定义卖单价格
            sell_side = "sell"
            cost = (1 + takeorder_fee) * takeorder_price
            sell_fee = cost * fee_rate
            sell_price = cost + sell_fee + 0.05

            sell_amount = order_amount - order_fee

            if eos_last > sell_price:
                # 下卖单
                sell_price = eos_last
                # take_sell_order = okex.create_order(
                #     order_symbol, order_type, sell_side, sell_amount, sell_price)

            take_sell_order = okex.create_order(
                order_symbol, order_type, sell_side, sell_amount, sell_price)

            # 卖单信息存入数据库
            print("开始写入数据库")
            post = {
                "单价": sell_price,
                "订单号": take_sell_order['id'],
                "方向": take_sell_order['side'],
            }

            collection.insert_one(post)

            # 删除已完成订单
            query = {"订单号": takeorder_id}
            collection.delete_one(query)
            print("已删除完成订单， 订单号为:", takeorder_id)

            time.sleep(3)

        elif order_status == "closed" and takeorder_side == "sell":
            buy_side = "buy"
            buy_price = eos_last * order_amount * 10 - 0.05

            take_buy_order = okex.create_order(
                order_symbol, order_type, buy_side, order_amount, buy_price)

            # 卖单信息存入数据库
            print("开始写入数据库")
            post = {
                "单价": buy_price,
                "订单号": take_buy_order['id'],
                "方向": take_buy_order['side']}

            collection.insert_one(post)

            # 删除已完成订单
            query = {"订单号": takeorder_id}
            collection.delete_one(query)
            print("已删除完成订单， 订单号为:", takeorder_id)

            time.sleep(3)
        else:
            print("订单处于其他状态")
            time.sleep(1)
