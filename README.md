# Paris Markets - Home Assistant Integration

A Home Assistant custom integration that provides real-time information about food markets in Paris using official open data from the City of Paris.

## Features

- Location-based market discovery using Home Assistant's configured coordinates
- Real-time market status based on current day and time
- Multiple filtering options: distance radius and product types
- Comprehensive market data including schedules, location, and contact information
- Calendar entities for viewing market schedules

## Installation

### Manual Installation
1. Copy the `custom_components/paris_markets` folder to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

### Prerequisites
Set your Home Assistant location if not already configured:
- Go to Settings → System → General
- Set your latitude and longitude

### Setup
1. Go to Settings → Devices & Services → Add Integration
2. Search for ‘Paris Markets’ and select it
3. Configure your preferences:
   - **Search radius**: Distance in kilometres (default: 2 km)
   - **Market types**: Select from available types (defaults to food markets)

### Available Market Types
- Food markets (Alimentaire)
- Organic food markets (Alimentaire bio)
- Flower markets (Fleurs)
- Bird markets (Oiseaux)
- Stamp markets (Timbres)
- Flea markets (Puces)
- Antique markets (Brocante)
- Artistic creation markets (Création artistique)

### Options
After installation, configure additional options:
- **Update interval**: Data fetch frequency (minimum 1 day, default 1 day)

## Entities

### Sensors
One sensor per market within your search radius, providing:

**State Values:**
- `open`: Market is currently open
- `closed`: Market is currently closed

**Attributes:**
- `long_name`: Full market name
- `short_name`: Short market name
- `location`: Detailed location description
- `arrondissement`: Paris arrondissement number
- `product_type`: Type of products sold
- `coordinates`: Geographic coordinates (latitude/longitude)

### Calendar Entities
Calendar entities for each market showing scheduled operating times:

**Features:**
- Automatic event generation for market operating days
- Event details include market name, location, arrondissement, and type
- Integration with Home Assistant calendar interface
- Support for calendar-based automations

## Usage Examples

### Template Sensor for Open Markets Count
```yaml
template:
  - sensor:
      - name: "Open Markets Count"
        state: >
          {{ states.sensor 
             | selectattr('entity_id', 'match', 'sensor.paris_markets_.*') 
             | selectattr('state', 'eq', 'open') 
             | list | count }}
        unit_of_measurement: markets
```

### Automation: Daily Market Notification
```yaml
- alias: "Daily Market Status"
  trigger:
    - platform: time
      at: "08:00:00"
  action:
    - service: notify.mobile_app_your_device
      data:
        title: "Markets Open Today"
        message: >
          {% set open_markets = states.sensor 
             | selectattr('entity_id', 'match', 'sensor.paris_markets_.*') 
             | selectattr('state', 'eq', 'open') 
             | map(attribute='attributes.long_name') 
             | list %}
          {{ open_markets | join(', ') if open_markets else 'No markets open today' }}
```

### Calendar-Based Automation
```yaml
- alias: "Market Opening Alert"
  trigger:
    platform: calendar
    entity_id: calendar.marche_saint_germain_calendar
    event: start
  action:
    service: notify.mobile_app_your_device
    data:
      message: "Marché Saint-Germain is now open!"
```

## Data Source

**Provider:** Official Paris Open Data platform  
**Dataset:** Marchés découverts (Open-air markets)  
**API:** OpenDataSoft API v2.1  
**URL:** https://opendata.paris.fr/explore/dataset/marches-decouverts

## Support

For issues and feature requests, use the GitHub issue tracker.

## License

This project is licensed under the MIT License.
