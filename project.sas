/* ============================================================
   SECTION 1 - CREATING THE SAS DATASET FROM AN EXTERNAL FILE
   ============================================================ */
PROC IMPORT datafile = "/home/u64490351/project/IKEA_product_catalog.csv" 
    out = work.ikea
    dbms = CSV
    replace;
    getnames = YES;
    guessingrows= 5000;
RUN;

PROC CONTENTS data = work.ikea;  /*verify the import*/
RUN;

PROC PRINT data = work.ikea (obs = 10); /*display the first 10 rows*/
RUN;

/* ============================================================
   SECTION 2 - CREATING AND USING USER-DEFINED FORMATS
   ============================================================ */
PROC FORMAT;

    value sell_fmt
        1 = 'Online'
        0 = 'Offline';

    value price_fmt
        low - <50 = 'Budget'
        50 - <200 = 'Standard'
        200 - high = 'Premium';

RUN;

DATA work.ikea_formats; /*apply the formats*/
    set work.ikea;

    online_sellable_bin = (upcase(strip(online_sellable)) = 'TRUE');

    format online_sellable_bin sell_fmt.;
    format price price_fmt.;

RUN;

PROC PRINT data = work.ikea_formats (obs = 15); /*print the first 15 observations*/
    var product_name online_sellable_bin price;
RUN;

/* ============================================================
   SECTION 3 - ITERATIVE AND CONDITIONAL PROCESSING OF DATA
   ============================================================ */
DATA work.ikea_processed; /*conditional processing*/
    set work.ikea_formats;

	length market_segment $20;
    length expansion_potential $30;

    if upcase(strip(online_sellable)) = 'TRUE' 
    then online_binary = 1;
    else online_binary = 0;

    if price < 50 then market_segment = 'Budget';
    else if price < 200 then market_segment = 'Standard';
    else market_segment = 'Premium';

	if lowcase(strip(product_rating)) = 'none' then
	    rating_num = .;
	else
	    rating_num = input(product_rating, best12.);

    if rating_num >= 4 and market_segment = 'Premium' then
        expansion_potential = 'High potential';
    else
        expansion_potential = 'Normal potential';
RUN;

DATA work.ikea_iterative; /*iterative processing*/
    set work.ikea_processed;
    array nums[*] _numeric_;

    do i = 1 to 3;
        if nums[i] = . then nums[i] = 0;
    end;
RUN;

PROC PRINT data = work.ikea_iterative (obs = 15); /*display the results*/
    var product_name online_binary market_segment
        expansion_potential price product_rating;
RUN;

PROC PRINT data = work.ikea_processed (obs = 15); 
    var product_name online_binary market_segment
        expansion_potential price product_rating;
RUN;

/* ============================================================
   SECTION 4 - CREATING DATA SUBSETS
   ============================================================ */

/*Subset 1*/
DATA work.premium_products; /*subset for premium products*/
    set work.ikea_iterative;
    where price >= 200;
RUN;

/*Subset 2*/
DATA work.budget_products; /*subset for budget products*/
    set work.ikea_iterative;
    where market_segment = 'Budget';
RUN;

/*Subset 3*/
DATA work.online_products; /*subset for online products*/
    set work.ikea_processed;
    where online_binary = 1;
RUN;

/*Subset 4*/
DATA work.high_potential_products; /*subset for high potential products*/
    set work.ikea_processed;
    where expansion_potential = 'High potential';
RUN;

PROC PRINT data = work.online_products(obs = 15); /*display the first 15 observations for high discount products*/
    var product_name country price;
    title 'Online products';
RUN;

PROC PRINT data = work.premium_products(obs = 15); /*display the first 15 observations for premium products*/
    var product_name main_category price;
    title 'Premium products';
RUN;

/* ============================================================
   SECTION 5 - USING SAS FUNCTIONS
   ============================================================ */
DATA work.ikea_functions;
    set work.ikea_processed;

    if lowcase(strip(product_rating)) = 'none' then  /*product rating in numeric*/
        rating_num = .;
    else
        rating_num = input(product_rating, best12.);

    country_upper = upcase(country); /*standard country names*/

    clean_category = strip(main_category); /*remove extra spaces*/

    short_name = substr(product_name, 1, 15); /*shorter product names*/

    clean_discount = compress(discount, '%'); /*remove % if exists*/
RUN;

PROC PRINT data = work.ikea_functions(obs = 15);
    var product_name short_name product_rating
        rating_num country country_upper
        main_category clean_category
        discount clean_discount;
RUN;

/* ============================================================
   SECTION 6 - COMBINING DATASETS WITH SQL PROCEDURES
   ============================================================ */
PROC SQL;
    CREATE TABLE work.country_price AS
    SELECT
        country,
        main_category,
        AVG(price) AS avg_price,
        COUNT(product_id) AS total_products
    FROM work.ikea_functions
    GROUP BY country, main_category;
QUIT;

PROC SQL;
    CREATE TABLE work.country_rating AS
    SELECT
        country,
        main_category,
        AVG(rating_num) AS avg_rating
    FROM work.ikea_functions
    GROUP BY country, main_category;
QUIT;

PROC SORT data=work.country_price;
    by country main_category;
RUN;

PROC SORT data=work.country_rating;
    by country main_category;
RUN;

DATA work.merged_country_data;
    merge
        work.country_price
        work.country_rating;

    by country main_category;
RUN;

PROC PRINT data=work.merged_country_data(obs = 20);
RUN;

/* ============================================================
   SECTION 7 - USING ARRAYS
   ============================================================ */
DATA work.ikea_arrays;
    set work.ikea_functions;

    array metrics[3] price rating_num online_binary;

    total_score = 0;

    do i = 1 to 3;
        if metrics[i] ne . then
            total_score + metrics[i];
    end;

    avg_score = total_score / 3;

	length performance_level $10;

    if avg_score >= 70 then
        performance_level = 'High';
    else if avg_score >= 30 then
        performance_level = 'Medium';
    else
        performance_level = 'Low';
RUN;

PROC PRINT data = work.ikea_arrays(obs = 15);
    var product_name
        price
        rating_num
        online_binary
        total_score
        avg_score
        performance_level;
RUN;

PROC FREQ data=work.ikea_arrays;
    tables performance_level;
RUN;

/* ============================================================
   SECTION 8 - REPORT PROCEDURES
   ============================================================ */
PROC MEANS data = work.ikea_arrays
    mean median min max;
    var price rating_num;
RUN;

PROC FREQ data = work.ikea_arrays;
    tables
        performance_level
        market_segment
        online_binary;
RUN;

PROC REPORT data=work.merged_country_data nowd;
    columns
        country
        main_category
        avg_price
        total_products
        avg_rating;

    define country / group;
    define main_category / group;
    define avg_price / analysis mean;
    define total_products / analysis sum;
    define avg_rating / analysis mean;
RUN;

PROC MEANS data=work.ikea_arrays mean;
    class market_segment;
    var price rating_num;
RUN;

/* ============================================================
   SECTION 9 - STATISTICAL PROCEDURES
   ============================================================ */
PROC CORR data = work.ikea_arrays;
    var
        price
        rating_num
        online_binary;
RUN;

PROC REG data = work.ikea_arrays plots(maxpoints = 2500);
    model price =
        rating_num
        online_binary;
RUN;
QUIT;

PROC MEANS data=work.ikea_arrays mean std;
    class performance_level;
    var price rating_num;
RUN;

/* ============================================================
   SECTION 10 - GENERATING GRAPHS
   ============================================================ */
PROC SGPLOT data=work.ikea_arrays;
    vbar market_segment / datalabel fillattrs = (color = cxb695c0);
    title "Distribution of market segments";
RUN;

PROC SGPLOT data=work.ikea_arrays;
    vbar online_binary / datalabel fillattrs = (color = cx8d4e85);
    title "Online product availability";
RUN;

PROC SGPLOT data=work.ikea_arrays;
    scatter
        x=rating_num
        y=price /
        markerattrs = (color = cx86608e);
    title "Price versus product rating";
RUN;

/* ============================================================
   SECTION 11 - SAS MACHINE LEARNING (PROC LOGISTIC)
   ============================================================ */
DATA work.ikea_ml;
    set work.ikea_arrays;

    if expansion_potential = 'High potential' then
        high_potential = 1;
    else
        high_potential = 0;
RUN;

PROC LOGISTIC data=work.ikea_ml descending;
    model high_potential =
        price
        rating_num
        online_binary;
RUN;