from pydantic import BaseModel, ConfigDict, Field, model_validator


class SOSAlertCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    accuracy_meters: float | None = Field(default=None, ge=0, le=100000)
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_location(self):
        coordinates_present = (
            self.latitude is not None,
            self.longitude is not None,
        )

        if coordinates_present[0] != coordinates_present[1]:
            raise ValueError("Latitude and longitude must be provided together")

        if self.accuracy_meters is not None and not all(coordinates_present):
            raise ValueError("Location accuracy requires latitude and longitude")

        return self


class SOSAlertResponse(BaseModel):
    id: int
    status: str
    source: str
    latitude: float | None
    longitude: float | None
    accuracy_meters: float | None
    created_at: str
    notification_status: str
