from pydantic import BaseModel, HttpUrl, EmailStr
from typing import List, Optional


class Location(BaseModel):
    address: Optional[str] = None
    postalCode: Optional[str] = None
    city: Optional[str] = None
    countryCode: Optional[str] = None
    region: Optional[str] = None


class Profile(BaseModel):
    network: Optional[str] = None
    username: Optional[str] = None
    url: Optional[HttpUrl] = None


class Basics(BaseModel):
    name: str
    label: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    url: Optional[HttpUrl] = None
    summary: Optional[str] = None
    location: Optional[Location] = None
    profiles: Optional[List[Profile]] = []


class Work(BaseModel):
    company: Optional[str] = None
    position: Optional[str] = None
    website: Optional[HttpUrl] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    summary: Optional[str] = None
    highlights: Optional[List[str]] = []


class Education(BaseModel):
    institution: str
    area: Optional[str] = None
    studyType: Optional[str] = None
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    score: Optional[str] = None
    courses: Optional[List[str]] = []


class Skill(BaseModel):
    name: str
    level: Optional[str] = None
    keywords: Optional[List[str]] = []


class Language(BaseModel):
    language: str
    fluency: Optional[str] = None


class Project(BaseModel):
    name: str
    description: Optional[str] = None
    highlights: Optional[List[str]] = []
    keywords: Optional[List[str]] = []
    startDate: Optional[str] = None
    endDate: Optional[str] = None
    url: Optional[HttpUrl] = None
    roles: Optional[List[str]] = []
    entity: Optional[str] = None
    type: Optional[str] = None


class JsonResume(BaseModel):
    basics: Basics
    work: List[Work] = []
    education: List[Education] = []
    skills: List[Skill] = []
    languages: List[Language] = []
    projects: List[Project] = []
