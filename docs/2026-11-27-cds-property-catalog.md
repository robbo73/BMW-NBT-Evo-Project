# CDS properties detected in the captured NBT Evo firmware

27 November 2026. **263 distinct property names** are registered by the captured `libhmiremoting.so` factory. This is a static inventory, not a list of confirmed live measurements on the M140i. Property availability, permissions, payload fields, units and update cadence require separate checks. Some names concern control operations rather than telemetry.

Download the [plain name list](cds-properties.txt) or [CSV with native factory IDs and evidence addresses](cds-properties.csv). The [registration evidence](evidence/2026-11-27-cds-property-catalog.json) records every name reference and insertion call.

## Evidence and limits

- Captured library: `libhmiremoting.so`, 7169308 bytes, SHA-256 `f5e0c7e78bc7054b96817064b7cd9cc6502e103759bab63a56a0320693aa1d37`.
- Constructor: `CCdsPropertyFactory::CCdsPropertyFactory()`, ELF virtual address `0x1a5a70`, size 44464 bytes. Each entry was recovered from its name-construction argument and associated vector insertion, rather than by accepting every dotted string in the binary.
- Cross-checks: 263 entries, 263 unique names and contiguous native factory IDs 1–263. The RPM entry independently matches the prior audit: name at `0x5a19fe`, ID 118, proc-unit word 1.
- These native factory IDs must not be substituted for IDs from other CDS/Connected app catalogues. The CSV's proc-unit value is the stored word; this inventory does not infer its routing semantics.
- Names and case are preserved exactly. A property name does not establish which JSON fields it supplies. For example, `engine.temperature` is one property; oil/coolant fields must be verified separately.
- Live RPM remains unverified. Prior engine-off and idle observations found an invalid cached engine-speed value and no `engine.RPMSpeed` entry in the inspected provider snapshot. This inventory performs no target operation and changes none of those results.
- This is the catalogue in this particular factory/library, not a claim to cover every BMW firmware or dynamically supplied property.

## Categories

| Category | Properties |
| --- | ---: |
| `climate` | 22 |
| `comfort` | 13 |
| `communication` | 21 |
| `controls` | 18 |
| `driving` | 41 |
| `engine` | 8 |
| `entertainment` | 56 |
| `hmi` | 10 |
| `navigation` | 31 |
| `specialvehicle` | 1 |
| `sensors` | 21 |
| `vehicle` | 17 |
| `mmi` | 1 |
| `rhmi` | 1 |
| `atm` | 1 |
| `cds` | 1 |

## climate

```text
climate.seatHeatDriver
climate.seatHeatPassenger
climate.seatHeatDRR
climate.seatHeatPSR
climate.seatClimate
climate.seatClimatePassenger
climate.seatClimateDRR
climate.seatClimatePSR
climate.driverSettings
climate.passengerSettings
climate.fondSettings
climate.ACCompressor
climate.ACMode
climate.ACSystemTemperatures
climate.residualHeat
climate.airConditionerCompressor
climate.ventilation
climate.seatAutoClimateDR
climate.seatAutoClimatePS
climate.seatAutoClimateDRR
climate.seatAutoClimatePSR
climate.armRestHeating
```

## comfort

```text
comfort.seatControlPS
comfort.seatControlDRR
comfort.seatControlPSR
comfort.seatMassageRL
comfort.seatMassageRR
comfort.seatLumbarRL
comfort.seatLumbarRR
comfort.scentGenerator
comfort.ambientLight
comfort.ambientColour
comfort.bodyTraining
comfort.bodyTrainingStatus
comfort.seatMemory
```

## communication

```text
communication.currentCallInfo
communication.lastCallInfo
communication.contactList
communication.contactDetail
communication.contactPicture
communication.contactServiceProvider
communication.controlCall
communication.call
communication.phoneStatus
communication.callStatus0
communication.callStatus1
communication.controlPhone
communication.phone
communication.callDuration0
communication.callDuration1
communication.callInfo0
communication.callInfo1
communication.callAvailability
communication.gsmSIAStatus
communication.infoPlus
communication.atmId
```

## controls

```text
controls.cruiseControl
controls.convertibleTop
controls.windshieldWiper
controls.lights
controls.startStopStatus
controls.startStopLEDs
controls.windowDriverFront
controls.windowPassengerFront
controls.windowDriverRear
controls.windowPassengerRear
controls.sunroof
controls.sunroof2
controls.turnSignal
controls.defrostRear
controls.headlights
controls.tcProxy
controls.shadowingRoof
controls.sunblind
```

## driving

```text
driving.odometer
driving.shiftIndicator
driving.acceleratorPedal
driving.speedActual
driving.keyPosition
driving.acceleration
driving.steeringWheel
driving.gear
driving.keyNumber
driving.brakeContact
driving.DSCActive
driving.clutchPedal
driving.speedDisplayed
driving.parkingBrake
driving.mode
driving.mode35up
driving.ecoTip
driving.averageConsumption
driving.averageSpeed
driving.ecoRange
driving.ecoRangeWon
driving.FDRControl
driving.electricalPowerDistribution
driving.displayRangeElectricVehicle
driving.drivingStyle
driving.trafficSignInfo1
driving.trafficSignInfo2
driving.trafficSignInfo3
driving.trafficSignInfo4
driving.trafficSignInfoVisibility
driving.rsConfigStatus
driving.orNPITextMessage
driving.orInfo
driving.sliTextMessage
driving.sliNextSpeedLimitRecognition
driving.sliActualSpeedLimitInfo
driving.laneBoundariesLoFrq
driving.laneBoundaries
driving.laneChange
driving.signRecognitionFrontCamera
driving.envLearning
```

## engine

```text
engine.status
engine.temperature
engine.RPMSpeed
engine.consumption
engine.info
engine.torque
engine.rangeCalc
engine.electricVehicleMode
```

## entertainment

```text
entertainment.descriptionCurrentSource
entertainment.multimedia
entertainment.statusAvailableSources
entertainment.statusAllowedSources
entertainment.mediabrowsing
entertainment.radioStation
entertainment.radioFrequency
entertainment.tuner.statusCurrentSource
entertainment.tuner.statusPlayback
entertainment.tuner.statusMetaInfo
entertainment.tuner.info
entertainment.tuner.playList
entertainment.tuner.coverArt
entertainment.tuner.epgEvent
entertainment.tuner.signalQuality
entertainment.rhmi.statusCurrentSource
entertainment.rhmi.coverArt
entertainment.rhmi.providerLogo
entertainment.rhmi.statusMetaInfo
entertainment.md.coverArt
entertainment.md.statusCurrentSource
entertainment.md.mediabrowsing
entertainment.md.statusPlayback
entertainment.md.controlPlayback
entertainment.md.statusMetaInfo
entertainment.md.playList
entertainment.md.random
entertainment.md.browsingCapabilities
entertainment.md.playingCapabilities
entertainment.drive.coverArt
entertainment.drive.statusCurrentSource
entertainment.drive.playList
entertainment.drive.statusPlayback
entertainment.drive.controlPlayback
entertainment.drive.statusMetaInfo
entertainment.drive.chapterList
entertainment.drive.subtitle
entertainment.drive.language
entertainment.drive.videoAngle
entertainment.drive.controlCurrentSource
entertainment.drive.random
entertainment.drive.colorButtonColorList
entertainment.drive.pipSuppress
entertainment.drive.blurayMemory
entertainment.drive.mediabrowsing
entertainment.video.statusCurrentSource
entertainment.video.statusPlayback
entertainment.video.playList
entertainment.video.statusMetaInfo
entertainment.video.subtitle
entertainment.video.language
entertainment.video.controlCurrentSource
entertainment.video.epgEvent
entertainment.video.signalQuality
entertainment.video.teletext
entertainment.video.stationScan
```

## hmi

```text
hmi.tts
hmi.speedlock
hmi.videolock
hmi.spellerInput
hmi.iDrive
hmi.graphicalContext
hmi.displayControl
hmi.httpTransfer
hmi.statistic
hmi.seeAllInfo
```

## navigation

```text
navigation.GPSPosition
navigation.GPSRawData
navigation.GPSExtendedInfo
navigation.nextDestinationDetailedInfo
navigation.currentPositionDetailedInfo
navigation.finalDestinationDetailedInfo
navigation.nextDestination
navigation.finalDestination
navigation.guidanceStatus
navigation.units
navigation.routeElapsedInfo
navigation.infoToNextDestination
navigation.infoToFinalDestination
navigation.mapFeature
navigation.triplist
navigation.showDestination
navigation.currentPositionCountry
navigation.getCABUrl
navigation.onlineStartUseCase.POIEnrichment
navigation.onlineStartUseCase.PictureOnDestination
navigation.onlineStartUseCase.OnlineSearch
navigation.onlineStartUseCase.IntermodalInformation
navigation.onlineStartUseCase.IntermodalRouteChange
navigation.onlineStartUseCase.IntermodalRouteInfo
navigation.onlineStartUseCase.CountryInformation
navigation.onlineStartUseCase.RouteInfoUploadBrowser
navigation.onlineStartUseCase.TripChoiceHMI
navigation.requestJourneys
navigation.onlineAppInformation
navigation.poiCategorySearch
navigation.naviguidanceinfo
```

## specialvehicle

```text
specialvehicle.menucontrol
```

## sensors

```text
sensors.fuel
sensors.PDCStatus
sensors.tirePressureWarning
sensors.seatOccupiedPassenger
sensors.seatbelt
sensors.temperatureExterior
sensors.temperatureInterior
sensors.doors
sensors.trunk
sensors.battery
sensors.PDCRangeFront
sensors.PDCRangeRear
sensors.PDCRangeFront2
sensors.PDCRangeRear2
sensors.seatOccupiedDriver
sensors.seatOccupiedRearLeft
sensors.seatOccupiedRearRight
sensors.lid
sensors.SOCBatteryHybrid
sensors.batteryTemp
sensors.childSafetyLock
```

## vehicle

```text
vehicle.VIN
vehicle.time
vehicle.type
vehicle.country
vehicle.unitSpeed
vehicle.systemTime
vehicle.language
vehicle.dayNightChangeOver
vehicle.interactionDetection
vehicle.powerStateHeadUnit
vehicle.partialNetworkRequest
vehicle.statePWF
vehicle.userTimeZone
vehicle.units
vehicle.fasStatus
vehicle.partType
vehicle.fastCharging
```

## mmi

```text
mmi.rseAccess
```

## rhmi

```text
rhmi.lumValues
```

## atm

```text
atm.atmSettings
```

## cds

```text
cds.apiRegistry
```
