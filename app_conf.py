import dynaconf
from dynaconf import Dynaconf, Validator
from loguru import logger

settings = Dynaconf(
    envvar_prefix="DYNACONF",
    settings_files=["conf_dir/settings.toml", "conf_dir/.secrets.toml"],
    validators=[
        # Ensure some parameter meets a condition
        # Validator('AGE', lte=30, gte=10),
        # validate a value is eq in specific env
        # Validator('PROJECT', eq='hello_world', env='production'),
    ],
)
settings.validators.register(
    Validator("app.debug", condition=lambda v: isinstance(v, bool), env="DEBUG"),
)
# raises after all possible errors are evaluated
try:
    settings.validators.validate_all()
except dynaconf.ValidationError as e:
    accumulative_errors = e.details
    logger.error(f"Setting Validation Error {accumulative_errors}")
    raise e

# :) Look https://www.dynaconf.com/validation/ for more validations


# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load these files in the order.
