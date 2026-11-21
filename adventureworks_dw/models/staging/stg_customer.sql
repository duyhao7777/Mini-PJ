   select
       cast(customerkey as int)                                   as customer_key,
       coalesce(nullif(trim(_prefix), ''), 'Unknown')              as prefix,
       trim(firstname)                                            as first_name,
       trim(lastname)                                             as last_name,
       try_convert(date, birthdate, 23)                           as birth_date,
       case trim(maritalstatus)
           when 'M' then 'Married'
           when 'S' then 'Single'
           else coalesce(nullif(trim(maritalstatus), ''), 'Unknown')
       end                                                        as marital_status,
       case trim(gender)
           when 'M' then 'Male'
           when 'F' then 'Female'
           else coalesce(nullif(trim(gender), ''), 'Unknown')
       end                                                        as gender,
       lower(trim(emailaddress))                                  as email_address,
       try_cast(annualincome as decimal(18, 2))                   as annual_income,
       try_cast(totalchildren as int)                             as total_children,
       coalesce(nullif(trim(educationlevel), ''), 'Unknown')      as education_level,
       coalesce(nullif(trim(occupation), ''), 'Unknown')          as occupation,
       case trim(homeowner)
           when 'Y' then 'Yes'
           when 'N' then 'No'
           else coalesce(nullif(trim(homeowner), ''), 'Unknown')
       end                                                        as home_owner
   from {{ source('stg', 'customer') }}
   where try_cast(customerkey as int) is not null