# 📊 Analytics Dashboard - Project Documentation

## 🏗️ Project Overview

This Streamlit-based Analytics Dashboard provides comprehensive insights into lead management and sales performance data. The dashboard integrates with a Supabase database and includes user authentication with role-based access control.

## 🗄️ Database Architecture

### Tables Used

#### 1. **`lead_master`** - Primary Leads Table
- **Purpose**: Stores all digital leads and their progression through the sales funnel
- **Key Columns**:
  - `id` - Primary key
  - `created_at` - Lead creation timestamp
  - `source` - Lead source (Google, Facebook, etc.)
  - `final_status` - Lead outcome (Pending, Won, Lost)
  - `cre_name` - Customer Relationship Executive assigned
  - `ps_name` - Product Specialist assigned
  - `ps_assigned_at` - PS assignment timestamp
  - `test_drive_status` - Boolean for test drive completion
  - `branch` - Branch location
  - `lead_status` - Current lead status
  - `first_call_date` - First contact date
  - `tat` - Turnaround time in seconds

#### 2. **`walkin_table`** - Walk-in Leads Table
- **Purpose**: Stores walk-in customer data and branch-wise performance
- **Key Columns**:
  - `id` - Primary key
  - `created_at` - Walk-in timestamp
  - `updated_at` - Last update timestamp
  - `won_timestamp` - Conversion timestamp
  - `status` - Walk-in status (Pending, Won, Lost)
  - `branch` - Branch location
  - `test_drive_done` - Boolean for test drive completion
  - `first_call_date` - First contact date

#### 3. **`ps_followup_master`** - Product Specialist Follow-up Table
- **Purpose**: Tracks PS assignments and follow-up activities
- **Key Columns**:
  - `ps_name` - Product Specialist name
  - `ps_branch` - PS branch location
  - `ps_assigned_at` - Assignment timestamp

#### 4. **`users`** - Authentication Table
- **Purpose**: User management and authentication
- **Key Columns**:
  - `id` - Primary key
  - `username` - Unique username
  - `email` - User email
  - `password_hash` - SHA-256 hashed password
  - `role` - User role (admin/user)
  - `created_at` - Account creation timestamp
  - `created_by` - Account creator
  - `is_active` - Account status

## 🔍 Data Fetching & Filtering System

### Global Filter System

The dashboard uses a **global date filter** that affects all KPIs and visualizations. The filter options are:

1. **MTD (Month to Date)** - Current month from 1st to now
2. **Today** - Current day only
3. **Custom Range** - User-defined date range
4. **All time** - No date filtering

### Filter Application Logic

#### **Date Column Mapping by Table**

| Table | Primary Date Column | Fallback Columns | Filter Logic |
|-------|-------------------|------------------|--------------|
| `lead_master` | `created_at` | - | Standard filtering |
| `walkin_table` | `created_at` | `updated_at`, `won_timestamp` | Priority-based fallback |
| `ps_followup_master` | `ps_assigned_at` | - | PS-specific filtering |

#### **Filter Implementation Details**

##### 1. **Lead Master Table Filtering**

```python
# Standard created_at filtering
q = supabase.table("lead_master").select("id", count="exact")
if filter_option_global != "All time" and start_dt_global is not None:
    q = q.gte("created_at", start_dt_global.isoformat()).lte("created_at", end_dt_global.isoformat())
```

**Used for**:
- Total leads count
- Lost leads count
- Won leads count
- Source-wise lead analysis

##### 2. **Walk-in Table Filtering**

```python
# Priority-based date column selection
filter_cols_priority = ["won_timestamp", "updated_at", "created_at"]
for col_name in filter_cols_priority:
    try:
        q = supabase.table("walkin_table").select("id", count="exact")
        q = q.gte(col_name, start_dt_global.isoformat()).lte(col_name, end_dt_global.isoformat())
        # Process result
        break
    except Exception:
        continue
```

**Used for**:
- Walk-in leads count
- Walk-in won count
- Branch-wise walk-in analysis

##### 3. **PS Follow-up Table Filtering**

```python
# PS assignment date filtering
q = supabase.table("ps_followup_master").select("ps_name", "ps_branch", "ps_assigned_at")
if filter_option_ps != "All time":
    q = q.gte("ps_assigned_at", start_dt_ps.isoformat()).lte("ps_assigned_at", end_dt_ps.isoformat())
```

**Used for**:
- PS Performance tab
- PS assignment counts

## 📊 KPI Calculations

### 1. **Leads KPI**
- **Query**: `lead_master` table
- **Filter**: `created_at` column
- **Calculation**: Count of all leads
- **Delta**: Comparison with previous period

### 2. **Assigned to CRE KPI**
- **Query**: `lead_master` table
- **Filter**: `created_at` column
- **Condition**: `cre_name` is not null
- **Calculation**: Count of leads with CRE assignment

### 3. **Assigned to PS KPI**
- **Query**: `lead_master` table
- **Filter**: `ps_assigned_at` column (different from global filter)
- **Condition**: `ps_name` is not null
- **Calculation**: Count of leads with PS assignment
- **Percentage**: PS assigned / Total leads

### 4. **Pending Leads KPI**
- **Query**: `lead_master` table
- **Filter**: `created_at` column
- **Condition**: `final_status = "Pending"`
- **Calculation**: Count of pending leads

### 5. **Lost Leads KPI**
- **Query**: `lead_master` table
- **Filter**: `created_at` column
- **Condition**: `final_status = "Lost"`
- **Calculation**: Count of lost leads
- **Percentage**: Lost leads / Total leads

### 6. **Won Leads KPI**
- **Query**: `lead_master` table
- **Filter**: `created_at` column
- **Condition**: `final_status = "Won"`
- **Calculation**: Count of won leads
- **Percentage**: Won leads / Total leads

### 7. **Walkin Leads KPI**
- **Query**: `walkin_table` table
- **Filter**: `created_at` column
- **Calculation**: Count of all walk-ins

### 8. **Walkin Won KPI**
- **Query**: `walkin_table` table
- **Filter**: Priority-based (`won_timestamp` → `updated_at` → `created_at`)
- **Condition**: `status = "Won"`
- **Calculation**: Count of converted walk-ins
- **Percentage**: Walkin won / Total walkins

### 9. **PS Untouched Leads**
- **Query**: `ps_followup_master` table
- **Filter**: Per PS name
- **Conditions**: 
  - `first_call_date IS NULL` (no first contact made)
  - `final_status = 'Pending'` OR `final_status IS NULL`
  - Excludes specific lead statuses (Lost to Codealer, Lost to Competition, Dropped, Booked, Retailed)
  - Excludes contact statuses (Call me Back, RNR, Busy on another Call, Call Disconnected, Call not Connected)
- **Calculation**: Count of leads assigned to PS but not yet contacted
- **Purpose**: Track PS workload and follow-up efficiency

## 🎯 Dashboard Sections

### 1. **Overall Tab**
- **Source-wise Lead Count**: Bar chart of leads by source
- **ETBR (Enquiry to Booking Ratio)**: Conversion analysis table
- **Walkin (branch-wise)**: Branch performance breakdown
- **Digital Leads Summary**: Branch-wise digital lead analysis

### 2. **Branch Performance Tab**
- **PS Performance**: Product Specialist assignment and performance
  - **Assigned**: Total leads assigned to each PS
  - **Untouched**: Leads assigned to PS but not yet contacted (no first_call_date)
- **Branch Filter**: Filter PS data by branch

### 3. **CRE Performance Tab**
- **CRE Metrics**: Customer Relationship Executive performance
- **Lead Status Tracking**: Touched, Untouched, Follow-up, Open leads
- **TAT Analysis**: Turnaround time calculations

## 🔐 Authentication System

### User Roles
- **Admin**: Full access + user management
- **User**: Dashboard access only

### Security Features
- SHA-256 password hashing
- Session-based authentication
- Role-based access control
- Soft delete for user accounts

## 🚀 Technical Stack

- **Frontend**: Streamlit
- **Backend**: Supabase (PostgreSQL)
- **Authentication**: Custom implementation with Supabase
- **Data Processing**: Pandas, NumPy
- **Visualization**: Altair, Streamlit native components

## 📈 Performance Considerations

### Database Optimization
- Indexed columns: `username`, `email`, `role` in users table
- Efficient date filtering with proper column selection
- Fallback mechanisms for missing date columns

### Caching
- Supabase client cached with `@st.cache_resource`
- Session state management for user data
- Efficient data processing with pandas

## 🔧 Configuration

### Environment Variables
- `SUPABASE_URL`: Supabase project URL
- `SUPABASE_ANON_KEY`: Supabase anonymous key

### Page Configuration
- Layout: Wide
- Initial sidebar state: Collapsed
- Custom CSS for styling

## 📝 Usage Notes

1. **Date Filtering**: The global filter affects most KPIs but some sections use specific date columns
2. **Fallback Logic**: Walk-in data uses priority-based date column selection
3. **Error Handling**: Comprehensive error handling with user-friendly messages
4. **Responsive Design**: Optimized for different screen sizes
5. **Real-time Updates**: Data refreshes on filter changes

## 🛠️ Maintenance

### Adding New KPIs
1. Define the query logic
2. Apply appropriate date filtering
3. Calculate delta comparison
4. Add to the KPI section

### Modifying Filters
1. Update the global filter logic
2. Ensure all table queries use the new filter
3. Test with different filter options

### Database Schema Changes
1. Update table documentation
2. Modify query logic accordingly
3. Test all dashboard sections
4. Update this documentation

---

*This documentation is maintained alongside the codebase and should be updated when making changes to the data fetching or filtering logic.*
