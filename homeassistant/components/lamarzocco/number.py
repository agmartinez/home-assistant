"""Number platform for La Marzocco espresso machines."""

from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any

from lmcloud import LMCloud as LaMarzoccoClient
from lmcloud.const import KEYS_PER_MODEL, LaMarzoccoModel

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PRECISION_TENTHS,
    PRECISION_WHOLE,
    EntityCategory,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import LaMarzoccoUpdateCoordinator
from .entity import LaMarzoccoEntity, LaMarzoccoEntityDescription


@dataclass(frozen=True, kw_only=True)
class LaMarzoccoNumberEntityDescription(
    LaMarzoccoEntityDescription,
    NumberEntityDescription,
):
    """Description of a La Marzocco number entity."""

    native_value_fn: Callable[[LaMarzoccoClient], float | int]
    set_value_fn: Callable[
        [LaMarzoccoUpdateCoordinator, float | int], Coroutine[Any, Any, bool]
    ]


@dataclass(frozen=True, kw_only=True)
class LaMarzoccoKeyNumberEntityDescription(
    LaMarzoccoEntityDescription,
    NumberEntityDescription,
):
    """Description of an La Marzocco number entity with keys."""

    native_value_fn: Callable[[LaMarzoccoClient, int], float | int]
    set_value_fn: Callable[
        [LaMarzoccoClient, float | int, int], Coroutine[Any, Any, bool]
    ]


ENTITIES: tuple[LaMarzoccoNumberEntityDescription, ...] = (
    LaMarzoccoNumberEntityDescription(
        key="coffee_temp",
        translation_key="coffee_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=PRECISION_TENTHS,
        native_min_value=85,
        native_max_value=104,
        set_value_fn=lambda coordinator, temp: coordinator.lm.set_coffee_temp(temp),
        native_value_fn=lambda lm: lm.current_status["coffee_set_temp"],
    ),
    LaMarzoccoNumberEntityDescription(
        key="steam_temp",
        translation_key="steam_temp",
        device_class=NumberDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        native_step=PRECISION_WHOLE,
        native_min_value=126,
        native_max_value=131,
        set_value_fn=lambda coordinator, temp: coordinator.lm.set_steam_temp(int(temp)),
        native_value_fn=lambda lm: lm.current_status["steam_set_temp"],
        supported_fn=lambda coordinator: coordinator.lm.model_name
        in (
            LaMarzoccoModel.GS3_AV,
            LaMarzoccoModel.GS3_MP,
        ),
    ),
    LaMarzoccoNumberEntityDescription(
        key="tea_water_duration",
        translation_key="tea_water_duration",
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        native_step=PRECISION_WHOLE,
        native_min_value=0,
        native_max_value=30,
        set_value_fn=lambda coordinator, value: coordinator.lm.set_dose_hot_water(
            value=int(value)
        ),
        native_value_fn=lambda lm: lm.current_status["dose_hot_water"],
        supported_fn=lambda coordinator: coordinator.lm.model_name
        in (
            LaMarzoccoModel.GS3_AV,
            LaMarzoccoModel.GS3_MP,
        ),
    ),
)


async def _set_prebrew_on(
    lm: LaMarzoccoClient,
    value: float,
    key: int,
) -> bool:
    return await lm.configure_prebrew(
        on_time=int(value * 1000),
        off_time=int(lm.current_status[f"prebrewing_toff_k{key}"] * 1000),
        key=key,
    )


async def _set_prebrew_off(
    lm: LaMarzoccoClient,
    value: float,
    key: int,
) -> bool:
    return await lm.configure_prebrew(
        on_time=int(lm.current_status[f"prebrewing_ton_k{key}"] * 1000),
        off_time=int(value * 1000),
        key=key,
    )


async def _set_preinfusion(
    lm: LaMarzoccoClient,
    value: float,
    key: int,
) -> bool:
    return await lm.configure_prebrew(
        off_time=int(value * 1000),
        key=key,
    )


KEY_ENTITIES: tuple[LaMarzoccoKeyNumberEntityDescription, ...] = (
    LaMarzoccoKeyNumberEntityDescription(
        key="prebrew_off",
        translation_key="prebrew_off",
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        native_step=PRECISION_TENTHS,
        native_min_value=1,
        native_max_value=10,
        entity_category=EntityCategory.CONFIG,
        set_value_fn=_set_prebrew_off,
        native_value_fn=lambda lm, key: lm.current_status[f"prebrewing_ton_k{key}"],
        available_fn=lambda lm: lm.current_status["enable_prebrewing"],
        supported_fn=lambda coordinator: coordinator.lm.model_name
        != LaMarzoccoModel.GS3_MP,
    ),
    LaMarzoccoKeyNumberEntityDescription(
        key="prebrew_on",
        translation_key="prebrew_on",
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        native_step=PRECISION_TENTHS,
        native_min_value=2,
        native_max_value=10,
        entity_category=EntityCategory.CONFIG,
        set_value_fn=_set_prebrew_on,
        native_value_fn=lambda lm, key: lm.current_status[f"prebrewing_toff_k{key}"],
        available_fn=lambda lm: lm.current_status["enable_prebrewing"],
        supported_fn=lambda coordinator: coordinator.lm.model_name
        != LaMarzoccoModel.GS3_MP,
    ),
    LaMarzoccoKeyNumberEntityDescription(
        key="preinfusion_off",
        translation_key="preinfusion_off",
        device_class=NumberDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        native_step=PRECISION_TENTHS,
        native_min_value=2,
        native_max_value=29,
        entity_category=EntityCategory.CONFIG,
        set_value_fn=_set_preinfusion,
        native_value_fn=lambda lm, key: lm.current_status[f"preinfusion_k{key}"],
        available_fn=lambda lm: lm.current_status["enable_preinfusion"],
        supported_fn=lambda coordinator: coordinator.lm.model_name
        != LaMarzoccoModel.GS3_MP,
    ),
    LaMarzoccoKeyNumberEntityDescription(
        key="dose",
        translation_key="dose",
        native_unit_of_measurement="ticks",
        native_step=PRECISION_WHOLE,
        native_min_value=0,
        native_max_value=999,
        entity_category=EntityCategory.CONFIG,
        set_value_fn=lambda lm, ticks, key: lm.set_dose(key=key, value=int(ticks)),
        native_value_fn=lambda lm, key: lm.current_status[f"dose_k{key}"],
        supported_fn=lambda coordinator: coordinator.lm.model_name
        == LaMarzoccoModel.GS3_AV,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up number entities."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]

    entities: list[NumberEntity] = [
        LaMarzoccoNumberEntity(coordinator, description)
        for description in ENTITIES
        if description.supported_fn(coordinator)
    ]

    for description in KEY_ENTITIES:
        if description.supported_fn(coordinator):
            num_keys = KEYS_PER_MODEL[coordinator.lm.model_name]
            entities.extend(
                LaMarzoccoKeyNumberEntity(coordinator, description, key)
                for key in range(min(num_keys, 1), num_keys + 1)
            )

    async_add_entities(entities)


class LaMarzoccoNumberEntity(LaMarzoccoEntity, NumberEntity):
    """La Marzocco number entity."""

    entity_description: LaMarzoccoNumberEntityDescription

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.entity_description.native_value_fn(self.coordinator.lm)

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        await self.entity_description.set_value_fn(self.coordinator, value)
        self.async_write_ha_state()


class LaMarzoccoKeyNumberEntity(LaMarzoccoEntity, NumberEntity):
    """Number representing espresso machine with key support."""

    entity_description: LaMarzoccoKeyNumberEntityDescription

    def __init__(
        self,
        coordinator: LaMarzoccoUpdateCoordinator,
        description: LaMarzoccoKeyNumberEntityDescription,
        pyhsical_key: int,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator, description)

        # Physical Key on the machine the entity represents.
        if pyhsical_key == 0:
            pyhsical_key = 1
        else:
            self._attr_translation_key = f"{description.translation_key}_key"
            self._attr_translation_placeholders = {"key": str(pyhsical_key)}
            self._attr_unique_id = f"{super()._attr_unique_id}_key{pyhsical_key}"
            self._attr_entity_registry_enabled_default = False
        self.pyhsical_key = pyhsical_key

    @property
    def native_value(self) -> float:
        """Return the current value."""
        return self.entity_description.native_value_fn(
            self.coordinator.lm, self.pyhsical_key
        )

    async def async_set_native_value(self, value: float) -> None:
        """Set the value."""
        await self.entity_description.set_value_fn(
            self.coordinator.lm, value, self.pyhsical_key
        )
        self.async_write_ha_state()
