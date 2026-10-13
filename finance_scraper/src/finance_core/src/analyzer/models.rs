
use rusdantic::prelude::*;
use serde::{Deserialize, Serialize};

#[derive(Model, Serialize, Deserialize)]
pub struct YFinanceTickerInfo {
    address1: Option<String>,
    city: Option<String>,
    state: Option<String>,
    country: Option<String>,
    postalCode: Option<String>,
    phoneNumber: Option<String>,
    website: Option<String>,
    description: Option<String>,
    industry: Option<String>,
    sector: Option<String>,
    fullTimeEmployees: Option<String>,
    founded: Option<String>,
    ceo: Option<String>,
    employees: Option<String>,
    revenue: Option<String>,
}
