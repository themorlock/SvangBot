from datetime import datetime, timedelta
import asyncio
import sys

from ccxt import bitmex

sys.path.append("indicators")
import ichimoku_cloud

class Bot:
	def __init__(self, config: dict, logger=None, client=None):
		self._config = config
		self._logger = logger

		self._symbol = config["symbol"]

		self._ichimoku_tenkan_sen_period = config["ichimoku_tenkan_sen_period"]
		self._ichimoku_kijun_sen_period = config["ichimoku_kijun_sen_period"]
		self._ichimoku_senkou_span_b_period = config["ichimoku_senkou_span_b_period"]
		self._ichimoku_senkou_span_lag_period = config["ichimoku_senkou_span_lag_period"]
		self._ichimoku_chikou_span_period = config["ichimoku_chikou_span_period"]
		self._data_period = config["data_period"]
		
		self._leverage = config["leverage"]
		self._n_multiplier = config["n_multiplier"]

		self._seconds_per_cycle = config["seconds_per_cycle"]

		if client:
			self._client = client
		else:
			self._client = bitmex({
				"test": config["test"],
				"apiKey": config["apiKey"],
				"secret": config["secret"]
			})

	def _get_current_price(self) -> float:
		return self._client.fetch_ticker(self._symbol)["close"]

	def _get_free_balance(self) -> float:
		return self._client.fetch_balance()[self._symbol[:self._symbol.index("/")]]["free"]

	def _ichimoku_calculate_purchase_size(self, hits):
		n = self._n_multiplier
		return self._leverage * ((n**hits) / (1 + n + n**2 + n**3 + n**4))


	async def start(self):
		previous_ichimoku_cloud = []

		current_price = self._get_current_price()
		usd_free_balance = self._get_free_balance() * current_price

		self._logger.info("----------------------------------------")
		self._logger.info("The initial balance is {} BTC.".format(round((usd_free_balance / current_price), 6)))

		bulls = 0
		bears = 0

		buy_orders = 0
		sell_orders = 0

		buys = 0
		sells = 0

		buy_order_prices = []
		sell_order_prices = []

		while True:
			current_price = self._get_current_price()
			usd_free_balance = self._get_free_balance() * current_price


			previous_ichimoku_cloud.append(ichimoku_cloud.get(self._client, self._symbol, self._data_period, self._ichimoku_tenkan_sen_period, self._ichimoku_kijun_sen_period, 
									self._ichimoku_senkou_span_b_period, self._ichimoku_senkou_span_lag_period,self._ichimoku_chikou_span_period))

			if len(previous_ichimoku_cloud) >= 2:
				ichimoku_cloud_signals = ichimoku_cloud.signal(previous_ichimoku_cloud)
				
				current_bulls = 0
				current_bears = 0
				for ichimoku_cloud_signal in ichimoku_cloud_signals:
					trend = ichimoku_cloud_signal[1]
					if trend == "bullish":
						current_bulls += 1
						bulls += 1
					elif trend == "bearish":
						current_bears += 1
						bears += 1
			
				current_order_size = int(usd_free_balance * self._ichimoku_calculate_purchase_size(current_bulls + current_bears))
				if current_bulls > 0 and (len(buy_order_prices) == 0 or current_price < (sum(sell_order_prices) / len(sell_order_prices))):
					self._logger.info("Buying {} contracts at ${}.".format(current_order_size, current_price))
					try:
						#self._client.create_order(self._symbol, 'limit', amount=(current_order_size + sells), price=current_price)
						#self._client.create_order(symbol=self._symbol, type="limit", amount=(current_order_size + buys), price=current_price)
						self._client.create_market_buy_order(symbol=self._symbol, amount=(current_order_size + sells))
						buy_orders += 1
						self._logger.info("Bought {} contracts at ${}.".format(current_order_size, current_price))
						sell_order_prices = [order_price for order_price in sell_order_prices if order_price > current_price]
						buy_order_prices.append(current_price)

						sells = 0
						buys += current_order_size
					except Exception:
						self._logger.info("Order Failed.")
				elif current_bears > 0 and (len(sell_order_prices) == 0 or current_price > (sum(buy_order_prices) / len(buy_order_prices))):
					self._logger.info("Selling {} contracts at ${}.".format(current_order_size, current_price))
					try:
						#self._client.create_order(self._symbol, 'limit', amount=-(current_order_size + sells), price=current_price)
						#self._client.create_order(symbol=self._symbol, type="limit", amount=-(current_order_size + buys), price=current_price)
						self._client.create_market_sell_order(symbol=self._symbol, amount=(current_order_size + buys))
						sell_orders += 1
						self._logger.info("Sold {} contracts at ${}.".format(current_order_size, current_price))
						buy_order_prices = [order_price for order_price in buy_order_prices if order_price < current_price]
						sell_order_prices.append(current_price)

						buys = 0
						sells += current_order_size
					except Exception:
						self._logger.info("Order Failed.")
				else:
					self._logger.info("No viable trade present.")

				bulls_to_bears = round((bulls / bears), 2) if bears > 0 else bulls
				self._logger.info("Bulls to Bears ratio is {}.".format(bulls_to_bears))
				buys_to_sells = round((buy_orders / sell_orders), 2) if sell_orders > 0 else buy_orders
				self._logger.info("Actual Buys to Sells ratio is {}.".format(buys_to_sells))
			else:
				self._logger.info("Waiting until enough data is present to make predictions.")

			self._logger.info("----------------------------------------")

			await asyncio.sleep(self._seconds_per_cycle - 1)
			