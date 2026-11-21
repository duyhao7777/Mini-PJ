   select
       cast(salesterritorykey as int) as territory_key,
       trim(region)                   as region,
       trim(country)                  as country,
       trim(continent)                as continent
   from {{ source('stg', 'territory') }}