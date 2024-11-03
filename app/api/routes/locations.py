from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlmodel import select, Session
from typing import Tuple

from app.core.db import get_db
from app.models.organisation import Organisation
from app.models.location import Location, CreateLocation

router = APIRouter()


@router.post("/create", response_model = Location)
def create_location(create_location: CreateLocation, 
                    session: Session = Depends(get_db)) -> Location:
    """
    Create locations
    """
    
    
    organisation = session.get(Organisation, create_location.organisation_id)
    if organisation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organisation not found")

    
    
    location = Location(organisation_id=organisation.id,
                        location_name=create_location.location_name,
                        longitude=create_location.longitude,
                        latitude=create_location.latitude
                        )
    
    session.add(location)
    session.commit()
    session.refresh(location)
    return location
    
    
@router.get("/{organisation_id}", response_model=list)
def get_organisation_locations(organisation_id: int, 
                               session: Session = Depends(get_db), 
                               bounding_box: Tuple[float, float, float, float] = Query(None)) -> list:
    
    """
    Query locations. With optional param.
    """
    
    # Define base query
    query = select(
        Location.location_name,
        Location.longitude,
        Location.latitude
        ).where(
            Location.organisation_id == organisation_id
        )
    
    # Enrich the query with additional where statement if a bounding box is given
    if bounding_box:
        min_lat, min_long, max_lat, max_long = bounding_box
        query = query.where(
            (Location.latitude >= min_lat) &
            (Location.latitude <= min_long) &
            (Location.longitude >= max_lat) &
            (Location.longitude <= max_long)
        )
    
    locations = session.exec(query).all()
    
    if not locations:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No locations found for organisation {organisation_id} with bounding box {bounding_box}")
    
    # Return list with extra formatting loop
    return [{"location_name": loc.location_name,
             "location_longitude": loc.longitude,
             "location_latitude": loc.latitude} for loc in locations]
    