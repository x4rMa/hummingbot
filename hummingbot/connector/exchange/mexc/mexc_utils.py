from decimal import Decimal
from typing import Any, Dict

from pydantic import ConfigDict, Field, SecretStr

from hummingbot.client.config.config_data_types import BaseConnectorConfigMap
from hummingbot.core.data_type.trade_fee import TradeFeeSchema

CENTRALIZED = True
EXAMPLE_PAIR = "ZRX-ETH"

DEFAULT_FEES = TradeFeeSchema(
    maker_percent_fee_decimal=Decimal("0.0005"),
    taker_percent_fee_decimal=Decimal("0.0005"),
    buy_percent_fee_deducted_from_returns=True
)


def is_exchange_information_valid(exchange_info: Dict[str, Any]) -> bool:
    """
    Verifies if a trading pair is enabled to operate with based on its exchange information
    :param exchange_info: the exchange information for a trading pair
    :return: True if the trading pair is enabled, False otherwise
    """
    return exchange_info.get("status", None) == "1" and "SPOT" in exchange_info.get("permissions", list()) \
        and exchange_info.get("isSpotTradingAllowed", True) is True


class MexcConfigMap(BaseConnectorConfigMap):
    connector: str = "mexc"
    mexc_api_key: SecretStr = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter your Mexc API key",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        }
    )
    mexc_api_secret: SecretStr = Field(
        default=...,
        json_schema_extra={
            "prompt": "Enter your Mexc API secret",
            "is_secure": True,
            "is_connect_key": True,
            "prompt_on_new": True,
        }
    )
    model_config = ConfigDict(title="mexc")


KEYS = MexcConfigMap.model_construct()
