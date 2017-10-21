console.log('Matthew image upgrade time was loaded ' + image_size)

Highcharts.chart('container1', {
    chart: {
        type: 'line'
    },
    title: {
        text: 'Merit Upgrade Additional Details ' + os_type
    },
    xAxis: {
        categories: score_date,
        crosshair: true
    },
    yAxis: {
        min: 0,
        title: {
            text: 'Values'
        }
    },
    credits: {
      enabled: false,
      text: 'mastarke'
    },
    tooltip: {
        headerFormat: '<span style="font-size:10px">{point.key}</span><table>',
        pointFormat: '<tr><td style="color:{series.color};padding:0">{series.name}: </td>' +
            '<td style="padding:0"><b>{point.y:1f}</b></td></tr>',
        footerFormat: '</table>',
        shared: false,
        useHTML: true
    },
    plotOptions: {
        series: {
            cursor: 'pointer',
            point: {
                events: {
                    click: function() {
                        var tableDate = this.category;
                        window.location.href = '/merit_table/' + tableDate;

                    }
                }
            }
        }
    },
    series: [{
        name: 'Upgrade Time (in minutes)',
        data: upgrade_time

    },{
        name: 'Loaded File Size (in MB)',
        data: image_size

    }]
});
