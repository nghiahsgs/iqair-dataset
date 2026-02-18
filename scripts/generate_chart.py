import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import timedelta
import os
import glob
import unidecode  # Thêm thư viện để bỏ dấu tiếng Việt

# Đọc tất cả các file CSV từ các thư mục thành phố
all_files = []
for city_dir in glob.glob('result/*/'):
    csv_files = glob.glob(os.path.join(city_dir, '*.csv'))
    all_files.extend(csv_files)

# Đọc và kết hợp tất cả các file CSV
df_list = []
for file in all_files:
    df = pd.read_csv(file)
    df_list.append(df)

# Kết hợp tất cả DataFrame
df = pd.concat(df_list, ignore_index=True)

# Chuyển đổi cột timestamp sang datetime
df['timestamp'] = pd.to_datetime(df['timestamp'])

# Lọc dữ liệu 1 tháng gần nhất
last_date = df['timestamp'].max()
one_month_ago = last_date - timedelta(days=30)
df_month = df[df['timestamp'] >= one_month_ago]

# Tạo thư mục charts nếu chưa tồn tại
os.makedirs('charts', exist_ok=True)

# Vẽ biểu đồ riêng cho từng thành phố
for city in df_month['city'].unique():
    plt.figure(figsize=(12, 6))
    sns.set_style("whitegrid")
    
    # Lọc dữ liệu cho thành phố hiện tại
    city_data = df_month[df_month['city'] == city]
    
    # Vẽ line plot
    plt.plot(city_data['timestamp'], city_data['aqi'], label='AQI', color='blue', marker='o')
    
    # Thêm vùng màu cho các mức độ ô nhiễm
    plt.axhspan(0, 50, color='green', alpha=0.1, label='Tốt')
    plt.axhspan(51, 100, color='yellow', alpha=0.1, label='Trung bình')
    plt.axhspan(101, 150, color='orange', alpha=0.1, label='Không tốt cho nhóm nhạy cảm')
    plt.axhspan(151, 200, color='red', alpha=0.1, label='Có hại')
    plt.axhspan(201, 300, color='purple', alpha=0.1, label='Rất có hại')
    plt.axhspan(301, 500, color='maroon', alpha=0.1, label='Nguy hiểm')
    
    # Thêm thông tin thống kê
    avg_aqi = city_data['aqi'].mean()
    max_aqi = city_data['aqi'].max()
    min_aqi = city_data['aqi'].min()
    plt.axhline(y=avg_aqi, color='red', linestyle='--', label=f'AQI TB: {avg_aqi:.1f}')
    
    plt.title(f'Chỉ số AQI tại {city} trong 30 ngày gần nhất\nMax: {max_aqi:.1f}, Min: {min_aqi:.1f}')
    plt.xlabel('Thời gian')
    plt.ylabel('Chỉ số AQI')
    plt.xticks(rotation=45)
    plt.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    
    # Chuyển tên thành phố thành không dấu và lowercase cho tên file
    city_filename = unidecode.unidecode(city.lower()).replace(' ', '-')
    
    # Lưu biểu đồ với tên file không dấu
    plt.savefig(f'charts/aqi_trend_{city_filename}.png', dpi=300, bbox_inches='tight')
    plt.close()  # Đóng figure để giải phóng bộ nhớ 