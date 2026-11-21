   with base as (

       select
           *,
           cast('{{ var("reference_date", "2022-06-30") }}' as date) as ref_date
       from {{ ref('stg_customer') }}

   )

   select
       customer_key,
       concat(first_name, ' ', last_name) as full_name,
       prefix,
       gender,
       marital_status,
       birth_date,
       datediff(year, birth_date, ref_date)
           - case
               when dateadd(year, datediff(year, birth_date, ref_date), birth_date) > ref_date
               then 1 else 0
             end                          as age,
       email_address,
       annual_income,
       case
           when annual_income is null    then 'Unknown'
           when annual_income < 40000    then '1. Under 40K'
           when annual_income < 70000    then '2. 40K-70K'
           when annual_income < 100000   then '3. 70K-100K'
           else                               '4. 100K+'
       end                                as income_band,
       total_children,
       education_level,
       occupation,
       home_owner
   from base