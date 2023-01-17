import logging
from typing import List, Tuple, Union

from hummingbot.connector.connector_base import ConnectorBase
from hummingbot.core.data_type.common import OrderType, PositionAction, PositionSide
from hummingbot.core.event.event_forwarder import SourceInfoEventForwarder
from hummingbot.core.event.events import (
    BuyOrderCompletedEvent,
    BuyOrderCreatedEvent,
    MarketEvent,
    OrderCancelledEvent,
    OrderFilledEvent,
    SellOrderCompletedEvent,
    SellOrderCreatedEvent,
)
from hummingbot.logger import HummingbotLogger
from hummingbot.strategy.script_strategy_base import ScriptStrategyBase
from hummingbot.strategy.smart_components.position_executor.data_types import (
    PositionConfig,
    PositionExecutorStatus,
    TrackedOrder,
)


class PositionExecutor:
    _logger = None

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._logger is None:
            cls._logger = logging.getLogger(__name__)
        return cls._logger

    def __init__(self,
                 position_config: PositionConfig,
                 strategy: ScriptStrategyBase):
        self._position_config: PositionConfig = position_config
        self._strategy: ScriptStrategyBase = strategy
        self._status: PositionExecutorStatus = PositionExecutorStatus.NOT_STARTED
        self._open_order: TrackedOrder = TrackedOrder()
        self._take_profit_order: TrackedOrder = TrackedOrder()
        self._time_limit_order: TrackedOrder = TrackedOrder()
        self._stop_loss_order: TrackedOrder = TrackedOrder()
        self._close_timestamp = None

        self._cancel_order_forwarder = SourceInfoEventForwarder(self.process_order_canceled_event)
        self._create_buy_order_forwarder = SourceInfoEventForwarder(self.process_order_created_event)
        self._create_sell_order_forwarder = SourceInfoEventForwarder(self.process_order_created_event)

        self._fill_order_forwarder = SourceInfoEventForwarder(self.process_order_filled_event)

        self._complete_buy_order_forwarder = SourceInfoEventForwarder(self.process_order_completed_event)
        self._complete_sell_order_forwarder = SourceInfoEventForwarder(self.process_order_completed_event)

        self._event_pairs: List[Tuple[MarketEvent, SourceInfoEventForwarder]] = [
            (MarketEvent.OrderCancelled, self._cancel_order_forwarder),
            (MarketEvent.BuyOrderCreated, self._create_buy_order_forwarder),
            (MarketEvent.SellOrderCreated, self._complete_buy_order_forwarder),
            (MarketEvent.OrderFilled, self._complete_sell_order_forwarder),
            (MarketEvent.BuyOrderCompleted, self._complete_buy_order_forwarder),
            (MarketEvent.SellOrderCompleted, self._complete_sell_order_forwarder)
        ]
        self.register_events()

    @property
    def position_config(self):
        return self._position_config

    @property
    def status(self):
        return self._status

    @property
    def is_closed(self):
        return self.status in [PositionExecutorStatus.CLOSED_BY_TIME_LIMIT,
                               PositionExecutorStatus.CLOSED_BY_STOP_LOSS,
                               PositionExecutorStatus.CLOSED_BY_TAKE_PROFIT,
                               PositionExecutorStatus.CANCELED_BY_TIME_LIMIT]

    @status.setter
    def status(self, status: PositionExecutorStatus):
        self._status = status

    @property
    def close_timestamp(self):
        return self._close_timestamp

    @close_timestamp.setter
    def close_timestamp(self, close_timestamp: float):
        self._close_timestamp = close_timestamp

    @property
    def connector(self) -> ConnectorBase:
        return self._strategy.connectors[self._position_config.exchange]

    @property
    def exchange(self):
        return self.position_config.exchange

    @property
    def trading_pair(self):
        return self.position_config.trading_pair

    @property
    def amount(self):
        return self.position_config.amount

    @property
    def entry_price(self):
        if self.status in [PositionExecutorStatus.NOT_STARTED,
                           PositionExecutorStatus.ORDER_PLACED,
                           PositionExecutorStatus.CANCELED_BY_TIME_LIMIT]:
            entry_price = self.position_config.entry_price
            price = entry_price if entry_price else self.connector.get_mid_price(self.trading_pair)
        else:
            price = self.open_order.order.average_executed_price
        return price

    @property
    def close_price(self):
        if self.status == PositionExecutorStatus.CLOSED_BY_STOP_LOSS:
            return self.stop_loss_order.order.average_executed_price
        elif self.status == PositionExecutorStatus.CLOSED_BY_TAKE_PROFIT:
            return self.take_profit_order.order.average_executed_price
        elif self.status == PositionExecutorStatus.CLOSED_BY_TIME_LIMIT:
            return self.time_limit_order.order.average_executed_price
        else:
            return None

    @property
    def pnl(self):
        if self.status in [PositionExecutorStatus.CLOSED_BY_TIME_LIMIT,
                           PositionExecutorStatus.CLOSED_BY_STOP_LOSS,
                           PositionExecutorStatus.CLOSED_BY_TAKE_PROFIT]:
            if self.side == PositionSide.LONG:
                return (self.close_price - self.entry_price) / self.entry_price
            else:
                return (self.entry_price - self.close_price) / self.entry_price
        elif self.status == PositionExecutorStatus.ACTIVE_POSITION:
            current_price = self.connector.get_mid_price(self.trading_pair)
            if self.side == PositionSide.LONG:
                return (current_price - self.entry_price) / self.entry_price
            else:
                return (self.entry_price - current_price) / self.entry_price
        else:
            return 0

    @property
    def timestamp(self):
        return self.position_config.timestamp

    @property
    def time_limit(self):
        return self.position_config.time_limit

    @property
    def end_time(self):
        return self.timestamp + self.time_limit

    @property
    def side(self):
        return self.position_config.side

    @property
    def open_order_type(self):
        return self.position_config.order_type

    @property
    def stop_loss_price(self):
        stop_loss_price = self.entry_price * (
            1 - self._position_config.stop_loss) if self.side == PositionSide.LONG else self.entry_price * (
            1 + self._position_config.stop_loss)
        return stop_loss_price

    @property
    def take_profit_price(self):
        take_profit_price = self.entry_price * (
            1 + self._position_config.take_profit) if self.side == PositionSide.LONG else self.entry_price * (
            1 - self._position_config.take_profit)
        return take_profit_price

    def get_order(self, order_id: str):
        order = self.connector._client_order_tracker.fetch_order(client_order_id=order_id)
        return order

    @property
    def open_order(self):
        return self._open_order

    @property
    def take_profit_order(self):
        return self._take_profit_order

    @property
    def stop_loss_order(self):
        return self._stop_loss_order

    @property
    def time_limit_order(self):
        return self._time_limit_order

    def control_position(self):
        if self.status == PositionExecutorStatus.NOT_STARTED:
            self.control_open_order()
        elif self.status == PositionExecutorStatus.ORDER_PLACED:
            self.control_cancel_order_by_time_limit()
        elif self.status == PositionExecutorStatus.ACTIVE_POSITION:
            self.control_take_profit()
            self.control_stop_loss()
            self.control_time_limit()
        elif self.status == PositionExecutorStatus.CLOSE_PLACED:
            pass

    def clean_executor(self):
        if self.status in [PositionExecutorStatus.CLOSED_BY_TIME_LIMIT,
                           PositionExecutorStatus.CLOSED_BY_STOP_LOSS]:
            if self.take_profit_order.order and (
                    self.take_profit_order.order.is_cancelled or
                    self.take_profit_order.order.is_pending_cancel_confirmation or
                    self.take_profit_order.order.is_failure
            ):
                pass
            else:
                self.logger().info(f"Take profit order status: {self.take_profit_order.order.current_state}")
                self.remove_take_profit()

    def remove_take_profit(self):
        self._strategy.cancel(
            connector_name=self.exchange,
            trading_pair=self.trading_pair,
            order_id=self._take_profit_order.order_id
        )
        self.logger().info("Removing take profit since the position is not longer available")

    def control_open_order(self):
        if not self.open_order.order_id:
            order_id = self._strategy.place_order(
                connector_name=self.exchange,
                trading_pair=self.trading_pair,
                amount=self.amount,
                price=self.entry_price,
                order_type=self.open_order_type,
                position_action=PositionAction.OPEN,
                position_side=self.side
            )
            self._open_order.order_id = order_id

    def control_cancel_order_by_time_limit(self):
        if self.end_time >= self._strategy.current_timestamp:
            self._strategy.cancel(
                connector_name=self.exchange,
                trading_pair=self.trading_pair,
                order_id=self._open_order.order_id
            )

    def control_take_profit(self):
        if not self.take_profit_order.order_id:
            order_id = self._strategy.place_order(
                connector_name=self._position_config.exchange,
                trading_pair=self._position_config.trading_pair,
                amount=self.open_order.order.executed_amount_base,
                price=self.take_profit_price,
                order_type=OrderType.LIMIT,
                position_action=PositionAction.CLOSE,
                position_side=PositionSide.LONG if self.side == PositionSide.SHORT else PositionSide.SHORT
            )
            self._take_profit_order.order_id = order_id

    def control_stop_loss(self):
        current_price = self.connector.get_mid_price(self.trading_pair)
        trigger_stop_loss = False
        if self.side == PositionSide.LONG and current_price <= self.stop_loss_price:
            trigger_stop_loss = True
        elif self.side == PositionSide.SHORT and current_price >= self.stop_loss_price:
            trigger_stop_loss = True

        if trigger_stop_loss:
            if not self.stop_loss_order.order_id:
                order_id = self._strategy.place_order(
                    connector_name=self.exchange,
                    trading_pair=self.trading_pair,
                    amount=self.open_order.order.executed_amount_base,
                    price=current_price,
                    order_type=OrderType.MARKET,
                    position_action=PositionAction.CLOSE,
                    position_side=PositionSide.LONG if self.side == PositionSide.SHORT else PositionSide.SHORT
                )
                self._stop_loss_order.order_id = order_id
                self._status = PositionExecutorStatus.CLOSE_PLACED

    def control_time_limit(self):
        position_expired = self.end_time < self._strategy.current_timestamp
        if position_expired:
            if not self._time_limit_order.order_id:
                price = self.connector.get_mid_price(self.trading_pair)
                order_id = self._strategy.place_order(
                    connector_name=self.exchange,
                    trading_pair=self.trading_pair,
                    amount=self.open_order.order.executed_amount_base,
                    price=price,
                    order_type=OrderType.MARKET,
                    position_action=PositionAction.CLOSE,
                    position_side=PositionSide.LONG if self.side == PositionSide.SHORT else PositionSide.SHORT
                )
                self._time_limit_order.order_id = order_id
                self._status = PositionExecutorStatus.CLOSE_PLACED

    def process_order_completed_event(self,
                                      event_tag: int,
                                      market: ConnectorBase,
                                      event: Union[BuyOrderCompletedEvent, SellOrderCompletedEvent]):
        if self.open_order.order_id == event.order_id:
            self.status = PositionExecutorStatus.ACTIVE_POSITION
        elif self.stop_loss_order.order_id == event.order_id:
            self.remove_take_profit()
            self.status = PositionExecutorStatus.CLOSED_BY_STOP_LOSS
            self.close_timestamp = event.timestamp
            self.logger().info("Closed by Stop loss")
        elif self.time_limit_order.order_id == event.order_id:
            self.remove_take_profit()
            self.status = PositionExecutorStatus.CLOSED_BY_TIME_LIMIT
            self.close_timestamp = event.timestamp
            self.logger().info("Closed by Time Limit")
        elif self.take_profit_order.order_id == event.order_id:
            self.status = PositionExecutorStatus.CLOSED_BY_TAKE_PROFIT
            self.close_timestamp = event.timestamp
            self.logger().info("Closed by Take Profit")

    def process_order_created_event(self,
                                    event_tag: int,
                                    market: ConnectorBase,
                                    event: Union[BuyOrderCreatedEvent, SellOrderCreatedEvent]):
        if self.open_order.order_id == event.order_id:
            self.open_order.order = self.get_order(event.order_id)
            self.status = PositionExecutorStatus.ORDER_PLACED
        elif self.take_profit_order.order_id == event.order_id:
            self.take_profit_order.order = self.get_order(event.order_id)
            self.logger().info("Take profit Created")
        elif self.stop_loss_order.order_id == event.order_id:
            self.logger().info("Stop loss Created")
            self.stop_loss_order.order = self.get_order(event.order_id)
        elif self.time_limit_order.order_id == event.order_id:
            self.logger().info("Time Limit Created")
            self.time_limit_order.order = self.get_order(event.order_id)

    def process_order_canceled_event(self,
                                     event_tag: int,
                                     market: ConnectorBase,
                                     event: OrderCancelledEvent):
        if self.open_order.order_id == event.order_id:
            self.status = PositionExecutorStatus.CANCELED_BY_TIME_LIMIT
            self.close_timestamp = event.timestamp

    def process_order_filled_event(self,
                                   event_tag: int,
                                   market: ConnectorBase,
                                   event: OrderFilledEvent):
        if self.open_order.order_id == event.order_id:
            if self.status == PositionExecutorStatus.ACTIVE_POSITION:
                self.logger().info("Position incremented, updating take profit.")
            else:
                self.status = PositionExecutorStatus.ACTIVE_POSITION
                self.logger().info("Position taken, placing take profit next tick.")

    def register_events(self):
        """Start listening to events from the given market."""
        for event_pair in self._event_pairs:
            self.connector.add_listener(event_pair[0], event_pair[1])

    def unregister_events(self):
        """Stop listening to events from the given market."""
        for event_pair in self._event_pairs:
            self.connector.remove_listener(event_pair[0], event_pair[1])

    def place_order(self):
        pass
